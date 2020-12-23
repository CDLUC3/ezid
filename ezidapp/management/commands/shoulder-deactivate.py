"""Deactivate an existing shoulder
"""



import argparse
import logging

import django.contrib.auth.models
import django.core.management
import django.db.transaction

import ezidapp.models
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
            help="Full shoulder. E.g., ark:/99999/fk4",
        )
        parser.add_argument(
            '--debug', action='store_true', help='Debug level logging',
        )

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog.util.log_to_console(__name__, opt.debug)

        shoulder_str = opt.shoulder_str
        try:
            shoulder_model = ezidapp.models.Shoulder.objects.get(prefix=shoulder_str)
        except ezidapp.models.Shoulder.DoesNotExist:
            raise django.core.management.CommandError(
                'Invalid shoulder: {}'.format(shoulder_str)
            )
        if not shoulder_model.active:
            raise django.core.management.CommandError(
                'Shoulder already deactivated: {}'.format(shoulder_str)
            )
        shoulder_model.active = False
        shoulder_model.save()

        log.info('Shoulder deactivated: {}'.format(shoulder_str))

        impl.nog.reload.trigger_reload()
