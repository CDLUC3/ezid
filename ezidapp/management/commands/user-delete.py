#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Delete user

For a user to be deleted, the user must:

   - Be disabled from logging in
   - Not inherit its group's shoulders
   - Have no shoulders
   - Not have any proxies or be a proxy for another user

Identifier deletions are logged to standard error and not to the server's log.
"""

import argparse
import logging

import django.core.management
import django.db.transaction

import ezidapp.models.group
import ezidapp.models.identifier
import ezidapp.models.realm
import ezidapp.models.user
import ezidapp.models.util
import ezidapp.models.util
import impl.django_util
import impl.ezid
import impl.nog.util

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
        parser.add_argument('user', help='The user to delete')
        parser.add_argument(
            '-i',
            action='store_true',
            dest='deleteIdentifiers',
            help='Also delete the user\'s identifiers',
        )
        parser.add_argument(
            '-l',
            action='store_false',
            dest='updateExternalServices',
            help='Disable external service updates',
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Debug level logging",
        )

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog.util.log_setup(__name__, opt.debug)

        user = ezidapp.models.util.getUserByUsername(opt.user)

        if user is None or opt.user == 'anonymous':
            raise django.core.management.CommandError('No such user: ' + opt.user)

        if (
            user.loginEnabled
            or user.inheritGroupShoulders
            or user.shoulders.count() > 0
            or user.proxies.count() > 0
            or user.proxy_for.count() > 0
        ):
            raise django.core.management.CommandError(
                'Cannot delete user. Please check the preconditions for deleting a user '
                'described in the help for this command'
            )

        if opt.deleteIdentifiers:
            # The loop below is designed to keep the length of the update queue
            # reasonable when deleting large numbers of identifiers.
            while True:
                ids = list(
                    ezidapp.models.identifier.Identifier.objects.filter(owner=user)
                    .only('identifier')
                    .order_by('identifier')[:1000]
                )
                for id_str in ids:
                    s = impl.ezid.deleteIdentifier(
                        id_str.identifier,
                        ezidapp.models.util.getAdminUser(),
                        opt.updateExternalServices,
                    )
                    if not s.startswith('success'):
                        raise django.core.management.CommandError(
                            'Identifier deletion failed: ' + s
                        )

                if len(ids) == 0:
                    break
        else:
            if ezidapp.models.identifier.Identifier.objects.filter(owner=user).count() > 0:
                raise django.core.management.CommandError(
                    'Cannot delete user because it has identifiers'
                )

        searchUser = ezidapp.models.user.User.objects.get(username=user.username)
        user.delete()
        searchUser.delete()

        s = impl.ezid.deleteIdentifier(user.pid, ezidapp.models.util.getAdminUser())
        if not s.startswith('success'):
            raise django.core.management.CommandError('Agent PID deletion failed: ' + s)

        log.info(f'Successfully deleted user "{opt.user}"')
