#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Create BerkeleyDB minter instances for any shoulders in the database that
are referencing non-existing minters.
"""

import argparse
import logging
import pathlib
import re

import django.conf
import django.contrib.auth.models
import django.core.management
import django.db.transaction

import ezidapp.models.shoulder
import impl.nog_bdb.bdb
import impl.nog_bdb.minter
import impl.nog_sql.util

log = logging.getLogger(__name__)


class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.opt = None

    def create_parser(self, *args, **kwargs):
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = argparse.RawTextHelpFormatter
        return parser

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run,d',
            dest='dry_run',
            action='store_true',
            help='Do not write to disk',
        )
        # Misc
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Debug level logging',
        )

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog_sql.util.log_setup(__name__, opt.debug)

        log.info('Creating missing minters...')

        if not opt.dry_run:
            pass

        try:
            self.create_missing_minters()
        except Exception as e:
            if django.conf.settings.DEBUG:
                import logging

                logging.exception('#' * 100)
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

        # TODO: Check for and count errors

        for s in ezidapp.models.shoulder.Shoulder.objects.all():
            total_count += 1

            if not s.minter.strip():
                log.warning(
                    'Shoulder does not specify a minter (supershoulder?). prefix="{}" name="{}"'.format(
                        s.prefix, s.name
                    )
                )
                unspecified_count += 1
                continue

            naan_str, shoulder_str = re.split(r'[/:.]', s.minter)[-2:]
            # noinspection PyProtectedMember
            bdb_path = impl.nog_bdb.bdb._get_bdb_path(naan_str, shoulder_str, root_path=None)
            if pathlib.Path(bdb_path).exists():
                continue

            log.info('Creating missing minter. prefix="{}" name="{}"'.format(s.prefix, s.name))

            missing_count += 1

            try:
                impl.nog_bdb.minter.create_minter_database(s.prefix, shoulder_str)
            except Exception as e:
                log.warning(
                    'Unable to create missing minter. prefix="{}" name="{}". Error: {}'.format(
                        s.prefix, s.name, str(e)
                    )
                )

        log.info('Total number of shoulders: {}'.format(total_count))
        log.info('Created missing shoulders: {}'.format(missing_count))
        log.info('Shoulders with unspecified minters: {}'.format(unspecified_count))
