#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Activate an existing shoulder
"""

import argparse
import logging

import django.contrib.auth.models
import django.core.management
import django.db.transaction

import ezidapp.models.shoulder
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
            '--debug',
            action='store_true',
            help='Debug level logging',
        )

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog.util.log_setup(__name__, opt.debug)

        shoulder_str = opt.shoulder_str
        log.debug("Getting shoulder %s", shoulder_str)
        try:
            shoulder_model = ezidapp.models.shoulder.Shoulder.objects.get(prefix=shoulder_str)
        except ezidapp.models.shoulder.Shoulder.DoesNotExist:
            log.debug("Shoulder string %s not found in Shoulder model", shoulder_str)
            raise django.core.management.CommandError('Invalid shoulder: {}'.format(shoulder_str))
        if shoulder_model.active:
            raise django.core.management.CommandError(
                'Shoulder already activated: {}'.format(shoulder_str)
            )
        shoulder_model.active = True
        shoulder_model.save()

        log.info('Shoulder activated: {}'.format(shoulder_str))
