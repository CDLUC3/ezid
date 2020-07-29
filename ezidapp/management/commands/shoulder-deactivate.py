"""Deactivate an existing shoulder
"""

from __future__ import absolute_import, division, print_function

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

    def handle(self, *_, **opt):
        shoulder_str = opt['shoulder_str']
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
        print('Shoulder deactivated: {}'.format(shoulder_str))
