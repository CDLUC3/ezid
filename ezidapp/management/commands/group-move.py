#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Move a group to a different realm

For a group to be moved, the group must:

    - Have no users that are realm administrators.

After running this command:

    - Save the group's record in the Django admin to update its agent PID.
    - Similarly save the group's user's records in the Django admin.
"""

import argparse
import logging

import django.core.management
import django.db.transaction

import ezidapp.models.group
import ezidapp.models.realm
import ezidapp.models.util
import impl.nog_sql.util


log = logging.getLogger(__name__)


class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.opt = None

    def create_parser(self, *args, **kwargs):
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = argparse.RawTextHelpFormatter
        return parser

    def add_arguments(self, parser):
        parser.add_argument('group', help='The group to move')
        parser.add_argument('new_realm', help='The realm to move to')
        parser.add_argument("--debug", action="store_true", help="Debug level logging")

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog_sql.util.log_setup(__name__, opt.debug)

        group = ezidapp.models.util.getGroupByGroupname(opt.group)

        if group is None or isinstance(group, ezidapp.models.group.AnonymousGroup):
            raise django.core.management.CommandError('No such group: ' + opt.group)

        try:
            newRealm = ezidapp.models.realm.Realm.objects.get(name=opt.new_realm)
        except ezidapp.models.realm.Realm.DoesNotExist:
            raise django.core.management.CommandError('No such realm: ' + opt.new_realm)

        if any(u.isRealmAdministrator for u in group.users.all()):
            raise django.core.management.CommandError(
                'Cannot move group because one or more users in the group are '
                'realm administrators'
            )

        if newRealm == group.realm:
            raise django.core.management.CommandError(
                'Group is already in realm. There is nothing to do'
            )

        with django.db.transaction.atomic():
            group.realm = newRealm
            group.save()
            for u in group.users.all():
                u.realm = newRealm
                u.save()

        newRealm = ezidapp.models.realm.Realm.objects.get(name=newRealm.name)
        searchGroup = ezidapp.models.group.Group.objects.get(groupname=group.groupname)

        with django.db.transaction.atomic():
            searchGroup.realm = newRealm
            searchGroup.save()
            for u in searchGroup.searchuser_set.all():
                u.realm = newRealm
                u.save()

        log.info(f'Successfully moved group "{group}" to realm "{opt.new_realm}')
        log.info(f'Please complete the additional steps described in the help for this command')
