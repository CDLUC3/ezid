"""Create BerkeleyDB minter instances for any shoulders in the database that are
referencing non-existing minters.
"""

from __future__ import absolute_import, division, print_function

import argparse
import logging
import pprint
import re

import django.core.management
import django.core.management.base
import hjson
import pathlib

import ezidapp.models
import impl.nog_minter
import utils.filesystem

try:
    import bsddb
except ImportError:
    import bsddb3 as bsddb

import django.contrib.auth.models
import django.core.management.base
import django.db.transaction
import impl.util

log = logging.getLogger(__name__)


class Command(django.core.management.base.BaseCommand):
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
        argparse.Namespace.is_doi = argparse.Namespace

        self.opt = opt = argparse.Namespace(**opt)

        if opt.debug:
            pprint.pprint(vars(opt))

        print('Creating missing minters...')

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

        print('Completed successfully')

    def create_missing_minters(self):
        total_count = 0
        missing_count = 0
        unspecified_count = 0

        for s in ezidapp.models.Shoulder.objects.all():
            total_count += 1

            if not s.minter.strip():
                print(
                    u'Warning: Minter unspecified in shoulder. prefix="{}" name="{}"'.format(
                        s.prefix, s.name
                    )
                )
                unspecified_count += 1
                continue

            naan_str, shoulder_str = re.split(r'[/:.]', s.minter)[-2:]
            bdb_path = impl.nog_minter.get_bdb_path(
                naan_str, shoulder_str, root_path=None
            )
            if pathlib.Path(bdb_path).exists():
                continue

            print(
                u'Creating missing minter. prefix="{}" name="{}"'.format(
                    s.prefix, s.name
                )
            )

            missing_count += 1

            try:
                self.create_minter_database(naan_str, shoulder_str)
            except Exception as e:
                print(
                    u'Warning: Unable to create missing minter. prefix="{}" name="{}". Error: {}'.format(
                        s.prefix, s.name, str(e)
                    )
                )

        print('Total number of shoulders: {}'.format(total_count))
        print('Created missing shoulders: {}'.format(missing_count))
        print('Shoulders with unspecified minters: {}'.format(unspecified_count))

    def create_minter_database(self, naan_str, shoulder_str):
        """Create a new BerkeleyDB minter database"""
        template_path = utils.filesystem.abs_path("./resources/minter_template.hjson")
        with open(template_path) as f:
            template_str = f.read()

        template_str = template_str.replace("$NAAN$", naan_str)
        template_str = template_str.replace("$PREFIX$", shoulder_str)

        minter_dict = hjson.loads(template_str)
        d = {bytes(k): bytes(v) for k, v in minter_dict.items()}

        bdb = impl.nog_minter.open_bdb(
            naan_str, shoulder_str, root_path=None, flags_str="c"
        )
        bdb.clear()
        bdb.update(d)
