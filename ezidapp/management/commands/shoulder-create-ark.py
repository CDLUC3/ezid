#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Create a new ARK shoulder
"""

import argparse
import logging

import django.core.management

import impl.nog_sql.exc
import impl.nog_sql.id_ns
import impl.nog_sql.shoulder
import impl.nog_sql.util

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
            help='Full ARK of new shoulder. E.g., ark:/12345/',
        )
        parser.add_argument('org_name_str', metavar='org-name', help='Name of organization')
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
        impl.nog_sql.util.log_setup(__name__, opt.debug)

        print(self.opt)

        try:
            return self._handle(self.opt)
        except impl.nog_sql.exc.MinterError as e:
            raise django.core.management.CommandError('Minter error: {}'.format(str(e)))

    def _handle(self, opt):
        try:
            ns = impl.nog_sql.id_ns.IdNamespace.split_ark_namespace(opt.ns_str)
        except impl.nog_sql.id_ns.IdentifierError as e:
            raise django.core.management.CommandError(str(e))

        impl.nog_sql.shoulder.create_shoulder(
            ns=ns,
            organization_name_str=opt.org_name_str,
            datacenter_model=None,
            is_crossref=False,
            is_test=opt.is_test,
            is_super_shoulder=opt.is_super_shoulder,
            is_sharing_datacenter=False,
            #is_force=opt.is_force,
            is_force=opt.skip_checks,
            is_debug=opt.debug,
        )

        # impl.nog.reload.trigger_reload()
        log.info('Shoulder created')
