#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Stub for dev and test of systemd wrappers
"""
import datetime
import logging
import time

import django.core.management

log = logging.getLogger(__name__)


SLEEP_SEC = 60


class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.opt = None

    def add_arguments(self, parser):
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Debug level logging',
        )

    def handle(self, *_, **opt):
        start_ts = datetime.datetime.now()
        while True:
            log.debug(f'proc-stub: Simulating async processing loop')
            log.debug(f'proc-stub: Current time: : {datetime.datetime.now()}')
            log.debug(f'proc-stub: Running since: : {start_ts}')
            log.debug(f'proc-stub: Sleeping for {SLEEP_SEC} sec...')
            time.sleep(SLEEP_SEC)
