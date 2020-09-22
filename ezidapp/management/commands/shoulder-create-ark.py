"""Create a new ARK shoulder
"""

from __future__ import absolute_import, division, print_function

import argparse
import logging
import re

import django.contrib.auth.models
import django.core.management
import django.db.transaction

import impl.nog.reload
import impl.nog.shoulder
import impl.nog.shoulder
import impl.nog.util
import nog.exc
import nog.id_ns
import nog.minter

log = logging.getLogger(__name__)


class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.opt = None

    def add_arguments(self, parser):
        parser.add_argument(
            "ns_str",
            metavar="shoulder-ark",
            nargs='?',
            help='Full ARK of new shoulder. E.g., ark:/12345/',
        )
        parser.add_argument('name_str', metavar='org-name', help='Name of organization')
        parser.add_argument(
            '--super-shoulder,s',
            dest='is_super_shoulder',
            action='store_true',
            help='Create a super-shoulder',
        )
        parser.add_argument(
            '--force,f',
            dest='is_force',
            action='store_true',
            help='Force creating super-shoulder on apparent regular shoulder',
        )
        parser.add_argument(
            '--test,-t',
            dest='is_test',
            action='store_true',
            help='Create a non-persistent test minter',
        )
        parser.add_argument(
            '--debug', action='store_true', help='Debug level logging',
        )

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog.util.add_console_handler(opt.debug)

        try:
            return self._handle(self.opt)
        except nog.exc.MinterError as e:
            raise django.core.management.CommandError(
                'Minter error: {}'.format(str(e))
            )

    def _handle(self, opt):
        try:
            ns = nog.id_ns.IdNamespace.from_str(opt.ns_str)
        except nog.id_ns.IdentifierError as e:
            raise django.core.management.CommandError(str(e))

        impl.nog.shoulder.assert_shoulder_is_type(ns, 'ark')
        impl.nog.shoulder.assert_shoulder_type_available(opt.name_str, 'ark')

        if not re.match(r'\d{5}$', ns.naan_prefix):
            raise django.core.management.CommandError(
                'NAAN must be 5 digits, not "{}"'.format(ns.naan_prefix)
            )

        log.info('Creating minter for ARK shoulder: {}'.format(opt.ns_str))
        bdb_path = nog.minter.create_minter_database(ns)
        log.debug('Minter BerkeleyDB created at: {}'.format(bdb_path.as_posix()))

        impl.nog.shoulder.create_shoulder_db_record(
            str(ns),
            'ark',
            opt.name_str,
            bdb_path,
            datacenter_model=None,
            is_crossref=False,
            is_test=opt.is_test,
            is_super_shoulder=opt.is_super_shoulder,
            is_sharing_datacenter=False,
            is_debug=opt.debug,
        )

        impl.nog.reload.trigger_reload()
        log.info('Shoulder created: {}'.format(opt.ns_str))
