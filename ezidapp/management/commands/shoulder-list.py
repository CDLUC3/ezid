"""List existing shoulders
"""
import argparse
import logging

import django.core.management.base

import impl.nog.shoulder
import impl.nog.util

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
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog.util.add_console_handler(opt.debug)
        impl.nog.shoulder.dump_shoulders()
