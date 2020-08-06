"""Create a new DOI shoulder
"""

from __future__ import absolute_import, division, print_function

import argparse
import logging
import pprint
import re

import django.core.management
import django.core.management.base
import ezidapp.models
import impl.nog_minter

try:
    import bsddb
except ImportError:
    import bsddb3 as bsddb

import django.contrib.auth.models
import django.core.management.base
import django.db.transaction
import impl.util

import ezidapp.management.commands.resources.shoulder as shoulder

log = logging.getLogger(__name__)


class Command(django.core.management.base.BaseCommand):
    # - Naming conventions:
    # https://docs.google.com/document/d/1uJiC5jGfTBuKBWAoddOyxUCO4ZbbL8c75O72YxgIr08/edit

    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.opt = None

    def add_arguments(self, parser):
        parser.add_argument('prefix_str', metavar='prefix', help="doi:10.<prefix>/...")
        parser.add_argument(
            'shoulder_str', metavar='shoulder', help="doi:10.../<shoulder>"
        )
        parser.add_argument('name_str', metavar='name', help='Name of organization')
        ex_group = parser.add_mutually_exclusive_group(required=True)
        ex_group.add_argument(
            '--crossref,-c',
            dest='is_crossref',
            action='store_true',
            help='Create a DOI shoulder registered with Crossref',
        )
        ex_group.add_argument(
            '--datacite,-a',
            metavar='datacenter',
            dest='datacenter_str',
            help='DOI is registered with DataCite',
        )
        parser.add_argument(
            '--super-shoulder,s',
            dest='is_super_shoulder',
            action='store_true',
            help='Set super-shoulder flag',
        )
        parser.add_argument(
            '--shares-datacenter,p',
            dest='is_sharing_datacenter',
            action='store_true',
            help='Shoulder is assigned to more than one datacenter',
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

        if opt.debug:
            pprint.pprint(vars(opt))

        # The shoulder must always be upper case for DOIs
        shoulder_str = opt.shoulder_str.upper()

        # shadow_str is the name of the minter, which always has 5 digits, while
        # the prefix may have only 4 digits. E.g.:
        # scheme_less = 10.9111/FK4 -> shadow = 10.b9111/FK4
        scheme_less_str = '10.{}/{}'.format(opt.prefix_str, shoulder_str)
        shadow_str = impl.util.doi2shadow(scheme_less_str)

        prefix_str, shoulder_str = shadow_str.split('/')
        full_shoulder_str = '/'.join([prefix_str, shoulder_str])

        if not re.match(r'[a-z0-9]\d{4}$', prefix_str):
            raise django.core.management.CommandError(
                'prefix for a DOI must be 5 digits, or one lower case character '
                'and 4 digits:'.format(prefix_str)
            )

        # namespace is the user selected name of the shoulder. E.g., doi:10.9111/FK4
        namespace_str = 'doi:{}'.format(scheme_less_str)
        print('Creating DOI minter: {}'.format(namespace_str))

        # opt.is_crossref and opt.datacenter_str are mutually exclusive with one
        # required during argument parsing.
        if opt.is_crossref:
            datacenter_model = None
        else:
            shoulder.assert_valid_datacenter(opt.datacenter_str)
            datacenter_model = ezidapp.models.StoreDatacenter.objects.get(
                symbol=opt.datacenter_str
            )

        shoulder.add_shoulder_db_record(
            namespace_str,
            'DOI',
            opt.name_str,
            full_shoulder_str,
            datacenter_model,
            is_crossref=opt.is_crossref,
            is_test=opt.is_test,
            is_super_shoulder=opt.is_super_shoulder,
            is_sharing_datacenter=opt.is_sharing_datacenter,
            is_debug=opt.debug,
        )

        shoulder.create_minter_database(prefix_str, shoulder_str)

        print('Shoulder created successfully. Restart the EZID service to activate.')
