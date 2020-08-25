"""List existing shoulders
"""
import argparse
import logging

import django.core.management.base

import ezidapp.management.commands.resources.shoulder as shoulder

log = logging.getLogger(__name__)


class Command(django.core.management.base.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()

    def add_arguments(self, parser):
        parser.add_argument(
            "--debug", action="store_true", help="Debug level logging",
        )

    def handle(self, *_, **opt):
        opt = argparse.Namespace(**opt)

        if opt.debug:
            logging.getLogger("").setLevel(logging.DEBUG)

        shoulder.dump_shoulders()
