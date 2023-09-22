#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Migrate BerkeleyDB minters to MySQL database.
   Convert each minter to a JSON object and store it in the ezidapp_minter table identified by the prefix/shoulder.
   Command options:
     --dry-run, -d: optional, perform BDB minter to JSON conversion but do not save the object to the database.
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
from django.core.exceptions import ValidationError

import ezidapp.models.shoulder
import ezidapp.models.minter
import impl.nog_bdb.bdb
import impl.nog_bdb.minter
import impl.nog_sql.util
import impl.nog_bdb.bdb_wrapper
import impl.nog_sql.exc

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
            help='Dry run without updating MySQL database',
        )
        parser.add_argument(
            '--output-file', '-o',
            dest='output_file',
            help='Filename to save minters in JSON',
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

        log.info('Migrating minters...')
        dry_run = opt.dry_run
        output_filename = opt.output_file

        if not dry_run:
            answer = input('Dry run without updating MySQL database: enter yes or no: ') 
            if answer == 'yes': 
                dry_run = True

        try:
            self.migrate_minters(output_filename, dry_run)
        except Exception as e:
            log.error(f'Error: {str(e)}')

        log.info('Completed successfully')

    def migrate_minters(self, output_filename, dry_run):
        total_count = 0
        unspecified_count = 0
        minter_count = 0
        missing_bdb_count = 0
        missing_key_count = 0
        validation_err_count = 0
        outfile = None

        if output_filename is not None:
            outfile = open(output_filename, "w")

        for s in ezidapp.models.shoulder.Shoulder.objects.all():
            total_count += 1
            minter_flag = ""
            if s.minter.strip() == '':
                minter_flag = ', '.join(
                    [
                        '{}={}'.format(k, 'yes' if v is True else 'no' if v is False else v)
                        for k, v in (
                            ('active', s.active),
                            ('supershoulder', s.isSupershoulder),
                            ('test', s.isTest),
                        )
                    ]
                )
                log.warning(
                    f'Shoulder does not specify a minter. prefix="{s.prefix}" name="{s.name}" flag="{minter_flag}"'
                )
                unspecified_count += 1
                continue

            naan_str, shoulder_str = re.split(r'[/:.]', s.minter)[-2:]
            try:
                bdb_path = impl.nog_bdb.bdb._get_bdb_path(naan_str, shoulder_str, root_path=None)
            except impl.nog_sql.exc.MinterError as e:
                log.info(f'get_bdb_path failed: prefix="{s.prefix}" name="{s.name}"')
                log.warning(f"error msg: {e}")
                continue

            if pathlib.Path(bdb_path).exists():
                log.info(f'Minter with BDB file: prefix="{s.prefix}" name="{s.name}"')
                bdb_dict, missing_keys = self.minter_to_dict(bdb_path)
                minter_count += 1
                if missing_keys > 0:
                    missing_key_count += missing_key_count
                if outfile:
                    outfile.write(json.dumps(bdb_dict) + "\n")
                minter = ezidapp.models.minter.Minter(prefix=s.prefix, minterState=bdb_dict)
                if not dry_run:
                    try:
                        minter.full_clean()
                    except ValidationError as exc_info:
                        validation_err_count += 1
                        log.error(f'Validation error: prefix="{s.prefix}" name="{s.name}" error: {exc_info}')
                        continue
                    ezidapp.models.minter.Minter.objects.create(prefix=s.prefix, minterState=bdb_dict)
            else:
                log.warning(f'Minter without DBD file: prefix="{s.prefix}" name="{s.name}"')
                missing_bdb_count += 1

        if outfile is not None:
            outfile.close()
        
        log.info(f'Total number of shoulders: {total_count}')
        log.info(f'Shoulders with unspecified minters: {unspecified_count}')
        log.info(f'Minters with BDB file: {minter_count}')
        log.info(f'Minters without BDB file: {missing_bdb_count}')
        log.info(f'Minters with missing required keys: {missing_key_count}')
        log.info(f'Minter validation errors: {validation_err_count}')
        log.info(f'Dry run without updating MySQL: {"yes" if dry_run else "no"}')
        log.info(f'JSON minters file: {output_filename}')

    def minter_to_dict(self, bdb_path):
        bdb_obj = impl.nog_bdb.bdb.open_bdb(bdb_path)
        
        def b2s(b):
            if isinstance(b, bytes):
                return b.decode('utf-8')
            return b
        
        # remove prefix ":/" from the keys
        # for example: 
        #   ":/c0/top" -> "c0/top", 
        #   ":/saclist" -> "saclist"
        def remove_prefix(s):
            return re.sub('^(:/)', '', s)
 
        bdb_dict = {remove_prefix(b2s(k)): b2s(v) for (k, v) in bdb_obj.items()}
       
        missing_key_count = self.check_keys(bdb_dict)
        bdb_json = json.dumps(bdb_dict)
        return bdb_dict, missing_key_count
    
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
            if required_key not in bdb_dict:
                log.warning(f'Missing key in BDB. Key: {required_key}')
                missing_key_count += 1
        
        return missing_key_count
