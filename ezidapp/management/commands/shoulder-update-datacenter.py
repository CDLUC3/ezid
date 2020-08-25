"""Update the DataCenter for an existing DOI shoulder
"""
import argparse
import logging

import django.core.management.base

import ezidapp.management.commands.resources.reload as reload
import ezidapp.management.commands.resources.shoulder as shoulder
import ezidapp.models

log = logging.getLogger(__name__)


class Command(django.core.management.base.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.opt = None

    def add_arguments(self, parser):
        parser.add_argument(
            'shoulder_str',
            metavar='shoulder',
            help="Full DOI shoulder. E.g., doi:10.9111/FK4",
        )
        parser.add_argument(
            'new_datacenter_str', metavar='datacenter', help="New DataCite datacenter",
        )
        parser.add_argument(
            '--debug', action='store_true', help='Debug level logging',
        )

    def handle(self, *_, **opt):
        opt = argparse.Namespace(**opt)

        if opt.debug:
            logging.getLogger('').setLevel(logging.DEBUG)

        shoulder.assert_valid_datacenter(opt.new_datacenter_str)

        try:
            scheme_str, full_shoulder = opt.shoulder_str.split(':',)
        except ValueError:
            raise django.core.management.CommandError(
                'Full DOI shoulder required. E.g., doi:10.9111/FK4": {}'.format(
                    opt.shoulder_str
                )
            )

        if scheme_str != 'doi':
            raise django.core.management.CommandError(
                'Scheme must be "doi": {}'.format(scheme_str)
            )
        namespace_str = '{}:{}'.format(scheme_str, full_shoulder.upper())

        try:
            shoulder_model = ezidapp.models.Shoulder.objects.get(prefix=namespace_str)
        except ezidapp.models.Shoulder.DoesNotExist:
            raise django.core.management.CommandError(
                'Invalid shoulder: {}'.format(namespace_str)
            )

        if shoulder_model.datacenter is None:
            raise django.core.management.CommandError(
                'Cannot set datacenter. '
                'Shoulder is registered with Crossref: {}'.format(namespace_str)
            )

        new_datacenter_model = ezidapp.models.StoreDatacenter.objects.get(
            symbol=opt.new_datacenter_str
        )

        old_datacenter_model = shoulder_model.datacenter
        if new_datacenter_model.symbol == old_datacenter_model.symbol:
            raise django.core.management.CommandError(
                'Datacenter is already {} for {}'.format(
                    new_datacenter_model.symbol, namespace_str
                )
            )

        shoulder_model.datacenter = new_datacenter_model
        shoulder_model.save()

        print(
            'Updated {} datacenter {} -> {}'.format(
                namespace_str, old_datacenter_model, new_datacenter_model
            )
        )

        reload.trigger_reload()
