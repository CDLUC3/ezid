"""Create a new ARK shoulder."""



import argparse
import logging

import django.core.management

import impl.nog.reload
import nog.shoulder
import impl.nog.util
import nog.exc
import nog.id_ns

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
        parser.add_argument(
            'org_name_str', metavar='org-name', help='Name of organization'
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
            help='Create a super-shoulder that does not end with "/"',
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
            raise django.core.management.CommandError('Minter error: {}'.format(str(e)))

    def _handle(self, opt):
        try:
            ns = nog.id_ns.IdNamespace.split_ark_namespace(opt.ns_str)
        except nog.id_ns.IdentifierError as e:
            raise django.core.management.CommandError(str(e))

        nog.shoulder.create_shoulder(
            ns=ns,
            organization_name_str=opt.org_name_str,
            datacenter_model=None,
            is_crossref=False,
            is_test=opt.is_test,
            is_super_shoulder=opt.is_super_shoulder,
            is_sharing_datacenter=False,
            is_force=opt.is_force,
            is_debug=opt.debug,
        )

        impl.nog.reload.trigger_reload()
        log.info('Shoulder created')
