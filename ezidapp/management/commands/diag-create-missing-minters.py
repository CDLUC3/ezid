"""Create BerkeleyDB minter instances for any shoulders in the database that are
referencing non-existing minters.
"""

from __future__ import absolute_import, division, print_function

import argparse
import logging
import re

import django.contrib.auth.models
import django.core.management
import django.core.management
import django.db.transaction
import pathlib2

import ezidapp.models
import impl.nog.util
import nog.bdb
import nog.bdb
import nog.minter

log = logging.getLogger(__name__)


class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.opt = None

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run,d',
            dest='dry_run',
            action='store_true',
            help='Do not write to disk',
        )
        # Misc
        parser.add_argument(
            '--debug', action='store_true', help='Debug level logging',
        )

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog.util.add_console_handler(opt.debug)

        log.info('Creating missing minters...')

        if not opt.dry_run:
            pass

        try:
            self.create_missing_minters()
        except Exception as e:
            if opt.debug:
                raise
            raise django.core.management.CommandError(
                'Unable to create missing minter(s). Error: {}'.format(str(e))
            )

        log.info('Completed successfully')

    def create_missing_minters(self):
        total_count = 0
        missing_count = 0
        unspecified_count = 0

        for s in ezidapp.models.Shoulder.objects.all():
            total_count += 1

            if not s.minter.strip():
                log.warn(
                    u'Shoulder does not specify a minter (supershoulder?). prefix="{}" name="{}"'.format(
                        s.prefix, s.name
                    )
                )
                unspecified_count += 1
                continue

            naan_str, shoulder_str = re.split(r'[/:.]', s.minter)[-2:]
            bdb_path = nog.bdb.get_bdb_path(naan_str, shoulder_str, root_path=None)
            if pathlib2.Path(bdb_path).exists():
                continue

            log.info(
                u'Creating missing minter. prefix="{}" name="{}"'.format(
                    s.prefix, s.name
                )
            )

            missing_count += 1

            try:
                nog.minter.create_minter_database(naan_str, shoulder_str)
            except Exception as e:
                log.warn(
                    u'Unable to create missing minter. prefix="{}" name="{}". Error: {}'.format(
                        s.prefix, s.name, str(e)
                    )
                )

        log.info('Total number of shoulders: {}'.format(total_count))
        log.info('Created missing shoulders: {}'.format(missing_count))
        log.info('Shoulders with unspecified minters: {}'.format(unspecified_count))
