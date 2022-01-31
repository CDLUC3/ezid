#!/usr/bin/env python

#  Copyright©2022, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

""""""
import contextlib
import logging
import os
import pathlib
import re
import subprocess
import sys
import time

import mysql.connector

log = logging.getLogger(__name__)


DB_HOST = os.environ['DB_HOST']
DB_PORT = os.environ['DB_PORT']
DB_USER = os.environ['DB_USER']
DB_PW = os.environ['DB_PW']
DB_NAME = os.environ['DB_NAME']


def main():
    print(f'host = {DB_HOST}')
    print(f'port = {DB_PORT}')
    print(f'user = {DB_USER}')
    print(f'database = {DB_NAME}')

    s = pathlib.Path('./schema-migration.sql').read_text()
    s_list = re.split(
        '^(#|\$|alter|create|delete|drop|insert|rename|select|update|use)',
        s,
        flags=re.MULTILINE | re.IGNORECASE,
    )

    full_ts = time.time()

    for i in range(0, len(s_list) - 1, 2):
        split_str = s_list[i + 1].strip()
        cmd_str = s_list[i + 2].strip()
        full_str = f'{split_str} {cmd_str}'

        print(full_str)

        if split_str == '#':
            continue

        start_ts = time.time()

        if split_str == '$':
            run_cmd(cmd_str)
        else:
            run_sql(full_str)

        print(f'Elapsed: {time.time() - start_ts:.2f}s\n')

    print(f'Full: {time.time() - full_ts:.2f}s\n')


def run_sql(sql_str):
    # print('run_sql')
    # return
    with connect() as cursor:
        cursor.execute('set unique_checks = 0', {})
        cursor.execute('set foreign_key_checks = 0', {})
        try:
            cursor.execute(sql_str, {})
        except Exception as e:
            raise
            print(str(e), file=sys.stderr)


def run_cmd(cmd_str):
    # print('run_cmd')
    # return
    try:
        subprocess.check_call(cmd_str.split(' '))
    except Exception as e:
        raise
        print(str(e), file=sys.stderr)


@contextlib.contextmanager
def connect():
    log.info(f'Connecting to database...')
    cnx = mysql.connector.connect(
        use_pure=False,
        # pool_size=1,
        # pool_name='mypool',
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PW,
        database=DB_NAME,
    )
    cnx.autocommit = True
    try:
        yield cnx.cursor()
    finally:
        cnx.close()


if __name__ == '__main__':
    sys.exit(main())
