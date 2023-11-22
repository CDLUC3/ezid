#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""List existing shoulders
"""

import argparse
import logging

import django.core.management

import impl.nog_sql.shoulder
import impl.nog_sql.util

log = logging.getLogger(__name__)


class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()

    def add_arguments(self, parser):
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Debug level logging",
        )

    # noinspection PyAttributeOutsideInit
    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog_sql.util.log_setup(__name__, opt.debug)

        impl.nog_sql.shoulder.dump_shoulders()
