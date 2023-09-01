#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Create a new DOI shoulder
"""

import argparse
import logging

import django.core.management

import ezidapp.models.datacenter
import impl.nog.exc
import impl.nog.id_ns
import impl.nog_sql.shoulder
import impl.nog.util

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
        parser.add_argument('org_name_str', metavar='org-name', help='Name of organization')
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
            '--skip-checks,f',
            dest='is_force',
            action='store_true',
            help='Create a super-shoulder that does not end with "/"',
        )
        parser.add_argument(
            '--test,-t',
            dest='is_test',
            action='store_true',
            help='Create a non-persistent test minter',
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Debug level logging',
        )

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog.util.log_setup(__name__, opt.debug)

        try:
            return self._handle(self.opt)
        except impl.nog.exc.MinterError as e:
            raise django.core.management.CommandError('Minter error: {}'.format(str(e)))

    def _handle(self, opt):
        try:
            ns = impl.nog.id_ns.IdNamespace.split_doi_namespace(opt.ns_str)
        except impl.nog.id_ns.IdentifierError as e:
            raise django.core.management.CommandError(str(e))

        # opt.is_crossref and opt.datacenter_str are mutually exclusive with one
        # required during argument parsing.
        if opt.is_crossref:
            datacenter_model = None
        else:
            impl.nog.shoulder.assert_valid_datacenter(opt.datacenter_str)
            datacenter_model = ezidapp.models.datacenter.Datacenter.objects.get(
                symbol=opt.datacenter_str
            )

        impl.nog_sql.shoulder.create_shoulder(
            ns=ns,
            organization_name_str=opt.org_name_str,
            datacenter_model=datacenter_model,
            is_crossref=opt.is_crossref,
            is_test=opt.is_test,
            is_super_shoulder=opt.is_super_shoulder,
            is_sharing_datacenter=opt.is_sharing_datacenter,
            is_force=opt.is_force,
            is_debug=opt.debug,
        )

        # impl.nog.reload.trigger_reload()
        log.info('Shoulder created')
