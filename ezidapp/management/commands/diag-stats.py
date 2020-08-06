"""Create BerkeleyDB minter instances for any shoulders in the database that are
referencing non-existing minters.
"""

from __future__ import absolute_import, division, print_function

import argparse
import logging
import pprint

import django.core.management
import ezidapp.models

try:
    import bsddb
except ImportError:
    import bsddb3 as bsddb

import django.db.transaction

log = logging.getLogger(__name__)


class Command(django.core.management.base.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.opt = None

    def add_arguments(self, parser):
        parser.add_argument(
            '--debug', action='store_true', help='Debug level logging',
        )

    def handle(self, *_, **opt):
        argparse.Namespace.is_doi = argparse.Namespace

        self.opt = opt = argparse.Namespace(**opt)

        if opt.debug:
            pprint.pprint(vars(opt))

        for statistics_model in ezidapp.models.Statistics.objects.all():
            print(statistics_model)

