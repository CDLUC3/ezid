#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Convert BerkeleyDB file to JSON.
   Command options:
     --input-file, -i: path to the BerkeleyDB file with .bdb extension.
     --output-file, -o: path to the converted JSON file.
"""

import argparse
import logging
import re
import json
import pathlib

import django.conf
import django.contrib.auth.models
import django.core.management
import django.db.transaction
from django.core.exceptions import ValidationError

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
            '--input-file', '-i',
            dest='input_file',
            required=True,
            help='Path to the BDB file',
        )
        parser.add_argument(
            '--output-file', '-o',
            dest='output_file',
            required=True,
            help='Path to the converted JSON file',
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

        log.info('Convert BDB file to JSON ...')
        input_filename = opt.input_file
        output_filename = opt.output_file

        bdb_dict, missing_key_count = self.minter_to_dict(pathlib.Path(input_filename))
        
        with open(output_filename, "w") as outfile:
            outfile.write(json.dumps(bdb_dict) + "\n")

        print(f'missing_key_count: {missing_key_count}')
        log.info('Completed successfully')

    
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

