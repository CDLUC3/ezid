#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Move a user to a different group, and possibly realm

For a user to be moved, the user must:

    - Be disabled from logging in
    - Not be privileged
    - Not inherit its current group's shoulders
    - Have no shoulders
    - Not have any proxies or be a proxy for another user

After running this command:

    - Save the user's record in the Django admin to update its agent PID.
    - Re-enable the user's login, shoulders, etc., as desired.

Identifier updates are logged to standard error and not to the server's log.
"""

import argparse
import logging

import django.core.management
import django.db.transaction

import ezidapp.models.group
import ezidapp.models.identifier
import ezidapp.models.user
import ezidapp.models.util
import impl.django_util
import impl.ezid
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
        parser.add_argument('user', help='The user to move')
        parser.add_argument('new_group', help='The group to move to')
        parser.add_argument("--debug", action="store_true", help="Debug level logging")

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog_sql.util.log_setup(__name__, opt.debug)

        user = ezidapp.models.util.getUserByUsername(opt.user)
        if user is None or opt.user == 'anonymous':
            raise django.core.management.CommandError('No such user: ' + opt.user)

        newGroup = ezidapp.models.util.getGroupByGroupname(opt.new_group)
        if newGroup is None or opt.new_group == 'anonymous':
            raise django.core.management.CommandError('No such group: ' + opt.new_group)

        if (
            user.loginEnabled
            or user.isPrivileged
            or user.inheritGroupShoulders
            or user.shoulders.count() > 0
            or user.proxies.count() > 0
            or user.proxy_for.count() > 0
        ):
            raise django.core.management.CommandError(
                'Cannot move user. Please check the preconditions for moving a user '
                'described in the help for this command'
            )

        if newGroup == user.group:
            raise django.core.management.CommandError(
                'User is already in group. There is nothing to do'
            )

        user.group = newGroup
        user.realm = newGroup.realm
        user.save()

        newGroup = ezidapp.models.group.Group.objects.get(groupname=newGroup.groupname)
        searchUser = ezidapp.models.user.User.objects.get(username=user.username)
        searchUser.group = newGroup
        searchUser.realm = newGroup.realm
        searchUser.save()

        lastId = ''
        while True:
            ids = list(
                ezidapp.models.identifier.Identifier.objects.filter(owner=user)
                .filter(identifier__gt=lastId)
                .only('identifier')
                .order_by('identifier')[:1000]
            )
            if len(ids) == 0:
                break
            for id in ids:
                s = impl.ezid.setMetadata(
                    id.identifier,
                    ezidapp.models.util.getAdminUser(),
                    {'_ownergroup': newGroup.groupname},
                    updateExternalServices=False,
                )
                if not s.startswith('success'):
                    raise django.core.management.CommandError('Identifier move failed: ' + s)
            lastId = ids[-1].identifier

        log.info(f'Successfully moved user "{opt.user}"')
        log.info(f'Please complete the additional steps described in the help for this command')
