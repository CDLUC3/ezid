"""Refresh the in-memory caches of the running EZID process
"""

from __future__ import absolute_import, division, print_function

import argparse
import logging

import django.core.management
import django.db.transaction

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
            '--debug', action='store_true', help='Debug level logging',
        )

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog.util.log_to_console(__name__, opt.debug)
        logging.getLogger('impl.nog.reload').setLevel(
            logging.DEBUG if opt.debug else logging.INFO)
        try:
            impl.nog.reload.trigger_reload()
        except impl.nog.reload.ReloadError as e:
            log.error('Server reload failed: {}'.format(str(e)))
        except Exception as e:
            log.error(
                'Server reload failed with unhandled exception: {}'.format(str(e)))
            if opt.debug:
                raise e
        else:
            log.info('Reload successful')
