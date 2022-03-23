#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Delete user

For a user to be deleted, the user must:

   - Not own any identifiers
   - Not own any shoulders
   - Not inherit its group's shoulders
   - Not have any proxies or be a proxy for another user
   - Be disabled from logging in

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
            ezidapp.models.identifier.SearchIdentifier.objects.filter(owner=user).exists()
            or ezidapp.models.identifier.Identifier.objects.filter(owner=user).exists()
        ):
            raise django.core.management.CommandError(
                'Cannot delete user: User is the owner of one or more identifiers'
            )

        if user.loginEnabled:
            raise django.core.management.CommandError(
                'Cannot delete user: User is enabled for login'
            )

        if user.inheritGroupShoulders or user.shoulders.count() > 0:
            raise django.core.management.CommandError(
                'Cannot delete user: User owns or inherits one or more shoulders'
            )

        if user.proxies.count() > 0:
            raise django.core.management.CommandError(
                'Cannot delete user: User has one or more proxy users'
            )

        if user.proxy_for.count() > 0:
            raise django.core.management.CommandError(
                'Cannot delete user: User is proxy for one or more users'
            )

        searchUser = ezidapp.models.user.User.objects.get(username=user.username)
        user.delete()
        searchUser.delete()

        s = impl.ezid.deleteIdentifier(user.pid, ezidapp.models.util.getAdminUser())
        if not s.startswith('success'):
            raise django.core.management.CommandError('Agent PID deletion failed: ' + s)

        log.info(f'Successfully deleted user "{opt.user}"')
