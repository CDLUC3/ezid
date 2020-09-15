"""Activate an existing shoulder
"""

from __future__ import absolute_import, division, print_function

import argparse
import logging

import django.core.management
import django.core.management.base

import ezidapp.models

try:
    import bsddb
except ImportError:
    import bsddb3 as bsddb

import django.contrib.auth.models
import django.core.management.base
import django.db.transaction
import impl.nog.reload
import impl.nog.util

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
            help="""
            Full shoulder. E.g., ark:/99999/fk4        
        """,
        )
        parser.add_argument(
            '--debug', action='store_true', help='Debug level logging',
        )

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog.util.add_console_handler(opt.debug)

        shoulder_str = opt.shoulder_str
        try:
            shoulder_model = ezidapp.models.Shoulder.objects.get(prefix=shoulder_str)
        except ezidapp.models.Shoulder.DoesNotExist:
            raise django.core.management.CommandError(
                'Invalid shoulder: {}'.format(shoulder_str)
            )
        if shoulder_model.active:
            raise django.core.management.CommandError(
                'Shoulder already activated: {}'.format(shoulder_str)
            )
        shoulder_model.active = True
        shoulder_model.save()

        log.info('Shoulder activated: {}'.format(shoulder_str))

        impl.nog.reload.trigger_reload()
