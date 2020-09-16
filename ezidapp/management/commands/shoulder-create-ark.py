"""Create a new ARK shoulder
"""

from __future__ import absolute_import, division, print_function

import argparse
import logging
import re

import django.contrib.auth.models
import django.core.management
import django.db.transaction

import impl.nog.shoulder
import nog.id_ns

try:
    import bsddb
except ImportError:
    import bsddb3 as bsddb

import django.contrib.auth.models
import django.core.management.base
import django.db.transaction

log = logging.getLogger(__name__)


class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.opt = None

    def add_arguments(self, parser):
        parser.add_argument('naan_str', metavar='naan', help="ark:/<naan>/...")
        parser.add_argument(
            'shoulder_str', metavar='shoulder', help="ark:/.../<shoulder>"
        )
        parser.add_argument('name_str', metavar='name', help='Name of organization')
        parser.add_argument(
            '--super-shoulder,s',
            dest='is_super_shoulder',
            action='store_true',
            help='Set super-shoulder flag',
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
        opt = argparse.Namespace(**opt)

    def _handle(self, opt):
        try:
            ns = nog.id_ns.IdNamespace.from_str(opt.ns_str)
        except nog.id_ns.IdentifierError as e:
            raise django.core.management.CommandError(str(e))

        if not re.match(r'\d{5}$', opt.naan_str):
            raise django.core.management.CommandError(
                'NAAN for an ARK must be 5 digits: {}'.format(opt.naan_str)
            )

        namespace_str = 'ark:/{}/{}'.format(opt.naan_str, opt.shoulder_str)
        print('Creating ARK minter: {}'.format(namespace_str))

        full_shoulder_str = nog_minter.create_minter_database(
            opt.naan_str, opt.shoulder_str
        )

        ezidapp.management.commands.resources.shoulder.create_shoulder_db_record(
            namespace_str,
            'ARK',
            opt.name_str,
            full_shoulder_str,
            datacenter_model=None,
            is_crossref=False,
            is_test=opt.is_test,
            is_super_shoulder=opt.is_super_shoulder,
            is_sharing_datacenter=False,
            is_debug=opt.debug,
        )

        print('Shoulder created: {}'.format(namespace_str))

        reload.trigger_reload()
