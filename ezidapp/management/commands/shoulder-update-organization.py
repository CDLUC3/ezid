"""Update the name of the organization for an existing ARK or DOI shoulder."""
import ezidapp.models.shoulder
import argparse
import logging

import django.core.management


import impl.nog.reload
import impl.nog.util

log = logging.getLogger(__name__)


class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.opt = None

    def add_arguments(self, parser):
        parser.add_argument(
            'shoulder_str',
            metavar='shoulder',
            help="Full ARK or DOI shoulder. E.g., ark:/99999/fk4 or doi:10.9111/FK4",
        )
        parser.add_argument(
            'new_org_name',
            metavar='organization-name',
            help="New name for organization",
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Debug level logging',
        )

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog.util.log_to_console(__name__, opt.debug)

        try:
            scheme_str, full_shoulder = opt.shoulder_str.split(
                ':',
            )
        except ValueError:
            raise django.core.management.CommandError(
                'Full ARK or DOI shoulder required: {}'.format(opt.shoulder_str)
            )

        if scheme_str == 'doi':
            full_shoulder = full_shoulder.upper()
        elif scheme_str == 'ark':
            full_shoulder = full_shoulder
        else:
            raise django.core.management.CommandError(
                'Scheme must be "ark" or "doi": {}'.format(scheme_str)
            )

        namespace_str = '{}:{}'.format(scheme_str, full_shoulder.upper())

        try:
            shoulder_model = ezidapp.models.shoulder.Shoulder.objects.get(
                prefix=namespace_str
            )
        except ezidapp.models.shoulder.Shoulder.DoesNotExist:
            raise django.core.management.CommandError(
                'Invalid shoulder: {}'.format(namespace_str)
            )

        old_org_str = shoulder_model.name
        if opt.new_org_name == old_org_str:
            raise django.core.management.CommandError(
                'Organization is already "{}" for {}'.format(old_org_str, namespace_str)
            )

        shoulder_model.name = opt.new_org_name
        shoulder_model.save()

        print(
            (
                'Updated {} organization name "{}" -> "{}"'.format(
                    namespace_str, old_org_str, opt.new_org_name
                )
            )
        )

        impl.nog.reload.trigger_reload()
