"""Refresh the in-memory caches of the running EZID process
"""

from __future__ import absolute_import, division, print_function

import argparse
import logging

import django.core.management

import ezidapp.management.commands.resources.reload as reload

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
        opt = argparse.Namespace(**opt)

        if opt.debug:
            logging.getLogger('').setLevel(logging.DEBUG)

        reload.trigger_reload()
