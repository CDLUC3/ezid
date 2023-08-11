#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Migrate BerkeleyDB minters to MySQL database.
   Convert each minter to a JSON object and store it in the ezidapp_minter table identified by the prefix/shoulder.
   Command options:
     --dry-run, -d: optional, perform minter to JSON conversion but do not save the object to the database.
     --output-file, -o: optional, save the JSON format minters to the specified file.
"""

import argparse
import logging
import pathlib
import re
import json

import django.conf
import django.contrib.auth.models
import django.core.management
import django.db.transaction

import ezidapp.models.shoulder
import impl.nog.bdb
import impl.nog.minter
import impl.nog.util
import impl.nog.bdb_wrapper
import impl.nog.exc

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
            '--dry-run', '-d',
            dest='dry_run',
            action='store_true',
            help='Do not write to disk',
        )
        parser.add_argument(
            '--output-file', '-o',
            dest='output_file',
            help='Output filename for minters in JSON',
        )
        # Misc
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Debug level logging',
        )

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog.util.log_setup(__name__, opt.debug)

        log.info('Migrating minters...')

        try:
            self.migrate_minters(opt.output_file, opt.dry_run)
        except Exception as e:
            log.error(f'Error: {str(e)}')

        log.info('Completed successfully')

    def migrate_minters(self, output_filename, dry_run):
        total_count = 0
        unspecified_count = 0
        minter_count = 0
        missing_bdb_count = 0
        missing_key_count = 0

        if output_filename:
            outfile = open(output_filename, "w")

        for s in ezidapp.models.shoulder.Shoulder.objects.all():
            total_count += 1

            if not s.minter.strip():
                log.warning(
                    f'Shoulder does not specify a minter (supershoulder?). prefix="{s.prefix}" name="{s.name}"'
                )
                unspecified_count += 1
                continue

            naan_str, shoulder_str = re.split(r'[/:.]', s.minter)[-2:]
            try:
                bdb_path = impl.nog.bdb._get_bdb_path(naan_str, shoulder_str, root_path=None)
            except impl.nog.exc.MinterError as e:
                log.info(f'get_bdb_path failed: prefix="{s.prefix}" name="{s.name}"')
                log.warning(f"error msg: {e}")
                continue

            if pathlib.Path(bdb_path).exists():
                log.info(f'Minter with BDB file: prefix="{s.prefix}" name="{s.name}"')
                bdb_dict, bdb_json, missing_keys = self.minter_to_json_2(bdb_path, False)
                minter_count += 1
                if missing_keys > 0:
                    missing_key_count += missing_key_count
                if bdb_json and outfile:
                    outfile.write(bdb_json + "\n")
            else:
                log.warning(f'Minter without DBD file: prefix="{s.prefix}" name="{s.name}"')
                missing_bdb_count += 1

        if outfile:
            outfile.close()
        log.info(f'Total number of shoulders: {total_count}')
        log.info(f'Shoulders with unspecified minters: {unspecified_count}')
        log.info(f'Minters with BDB file: {minter_count}')
        log.info(f'Minters without BDB file: {missing_bdb_count}')
        log.info(f'Minters with mising required keys: {missing_key_count}')
        log.info(f"Minters are saved in JSON file: {output_filename}")

    def minter_to_json_2(self, bdb_path, compact=True):
        bdb_obj = impl.nog.bdb.open_bdb(bdb_path)
        
        def b2s(b):
            if isinstance(b, bytes):
                return b.decode('utf-8')
            return b

        bdb_dict = {b2s(k): b2s(v) for (k, v) in bdb_obj.items()}
       
        missing_key_count = self.check_keys(bdb_dict)
        d_json = json.dumps(bdb_dict)
        return bdb_dict, d_json, missing_key_count
    
    def check_keys(self, bdb_dict):
        """check missing keys
           return: total number of missing keys in the bdb_dict
        """
        missing_key_count = 0
        for required_key in (
            'basecount',
            'oacounter',
            'oatop',
            'total',
            'percounter',
            'template',
            'mask',
            'atlast',
            'saclist',
            'siclist',
        ):
            k = ':/{}'.format(required_key)
            if k not in bdb_dict:
                log.warning(f'Missing key in BDB. Key: {k}')
                missing_key_count += 1
        
        return missing_key_count

