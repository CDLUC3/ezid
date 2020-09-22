"""Create a new DOI shoulder
"""

from __future__ import absolute_import, division, print_function

import argparse
import logging

import django.contrib.auth.models
import django.core.management
import django.db.transaction

import ezidapp.models
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
            metavar="shoulder-doi",
            help='Full DOI of new shoulder. E.g., doi:10.12345/',
        )
        parser.add_argument('name_str', metavar='org-name', help='Name of organization')
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
            '--shares-datacenter,-p',
            dest='is_sharing_datacenter',
            action='store_true',
            help='Shoulder is assigned to more than one datacenter',
        )

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
        impl.nog.util.log_to_console(__name__, opt.debug)

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

        impl.nog.shoulder.assert_shoulder_is_type(ns, 'doi')
        impl.nog.shoulder.assert_shoulder_type_available(opt.name_str, 'doi')

        # opt.is_crossref and opt.datacenter_str are mutually exclusive with one
        # required during argument parsing.
        if opt.is_crossref:
            datacenter_model = None
        else:
            impl.nog.shoulder.assert_valid_datacenter(opt.datacenter_str)
            datacenter_model = ezidapp.models.StoreDatacenter.objects.get(
                symbol=opt.datacenter_str
            )

        log.info('Creating minter for DOI shoulder: {}'.format(opt.ns_str))
        bdb_path = nog.minter.create_minter_database(ns)
        log.debug('Minter BerkeleyDB created at: {}'.format(bdb_path.as_posix()))

        impl.nog.shoulder.create_shoulder_db_record(
            str(ns),
            'doi',
            opt.name_str,
            bdb_path,
            datacenter_model,
            is_crossref=opt.is_crossref,
            is_test=opt.is_test,
            is_super_shoulder=opt.is_super_shoulder,
            is_sharing_datacenter=opt.is_sharing_datacenter,
            is_debug=opt.debug,
        )

        impl.nog.reload.trigger_reload()
        log.info('Shoulder created: {}'.format(opt.ns_str))
