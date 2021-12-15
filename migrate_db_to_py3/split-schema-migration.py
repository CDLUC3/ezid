#!/usr/bin/env python

"""Split the schema-migration.py file into sections to run separately"""

import logging
import pathlib
import re
import sys

MIGRATION_SQL_PATH = './sql/schema-migration.sql'

log = logging.getLogger(__name__)


def main():
    p = pathlib.Path(MIGRATION_SQL_PATH)
    full_str = p.read_text()
    section_list = re.split('^#@#', full_str, flags=re.MULTILINE)
    prefix_str, section_list = section_list[1], section_list[2:]
    for i, section_str in enumerate(section_list):
        section_path = p.with_suffix(f'.{i + 1}.sql')
        print(f'Creating file: {section_path.as_posix()}')
        section_path.write_text(prefix_str.strip() + '\n\n' + section_str.strip())


if __name__ == '__main__':
    sys.exit(main())
