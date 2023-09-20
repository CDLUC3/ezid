#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Delete a group

Before running this command, remove the group's users and shoulders.
"""

import argparse
import logging

import django.contrib.auth.models
import django.core.management
import django.db.transaction

import ezidapp.models.group
import ezidapp.models.shoulder
import ezidapp.models.util
import impl
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
        parser.add_argument('group', help='The group to delete')
        parser.add_argument("--debug", action="store_true", help="Debug level logging")

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog_sql.util.log_setup(__name__, opt.debug)

        group = ezidapp.models.util.getGroupByGroupname(opt.group)

        if group is None or isinstance(group, ezidapp.models.group.AnonymousGroup):
            raise django.core.management.CommandError('No such group: ' + opt.group)

        if group.users.count() > 0:
            raise django.core.management.CommandError(
                f'Cannot delete group because it is not empty. '
                f'First delete the {group.users.count()} user(s) in the group'
            )

        if group.shoulders.count() > 0:
            raise django.core.management.CommandError(
                f'Cannot delete group because it is not empty. '
                f'First delete the {group.shoulders.count()} shoulder(s) in the group'
            )

        group_model = ezidapp.models.group.Group.objects.get(groupname=group.groupname)
        group.delete()
        group_model.delete()

        result_str = impl.ezid.deleteIdentifier(group.pid, ezidapp.models.util.getAdminUser())

        if not result_str.startswith('success'):
            raise django.core.management.CommandError(f'Agent PID deletion failed: {result_str}')

        log.info(f'Successfully deleted group: {group}')
