#!/usr/bin/env python

""""""

# Copyright©2021, Regents of the University of California
# http://creativecommons.org/licenses/BSD

import contextlib
import logging
import sys
import time

import mysql.connector
import mysql.connector.cursor

log = logging.getLogger(__name__)

DB_HOST = '127.0.0.1'
DB_PORT = '3337'
DB_ROOT_USER = 'eziddba'
DB_ROOT_PW = ''
DB_NAME = 'ezid'


BATCH_SIZE = 10000


def main():
    start_ts = time.time()
    prev_ts = start_ts

    with connect(DB_NAME) as cnx:
        cursor = cnx.cursor()

        owner_case_str = get_case_str(cursor, 'user', 'pid')
        group_case_str = get_case_str(cursor, 'group', 'pid')
        profile_case_str = get_case_str(cursor, 'profile', 'label')
        datacenter_case_str = get_case_str(cursor, 'datacenter', 'symbol')

        last_id = 0

        while True:
            cursor = cnx.cursor()

            cnx.autocommit = False

            cursor.execute('set unique_checks = 0', {})
            cursor.execute('set foreign_key_checks = 0', {})

            # Counter-intuitive syntax for processing in chunks
            q = f"""
            update ezidapp_searchidentifier set
            owner_id = {owner_case_str},
            ownergroup_id = {group_case_str},
            profile_id = {profile_case_str},
            datacenter_id = {datacenter_case_str}
            where id = last_insert_id(id)
            and id > {last_id}
            limit {BATCH_SIZE} 
            ;
            """
            print(f'id > {last_id}')
            # print(q)
            cursor.execute(q, {})

            # q = """
            # select row_count();
            # """
            # cursor.execute(q, {})
            # row_count = cursor.fetchone()[0]
            # if not row_count:
            #     break

            q = """
            select last_insert_id();
            """
            cursor.execute(q, {})
            last_id = cursor.fetchone()[0]

            cnx.commit()
            del cursor

            cur_ts = time.time()
            print(f'Batch: {cur_ts - prev_ts:.2f}s')
            prev_ts = cur_ts

    print(f'Total {time.time() - start_ts:.2f}s')


def get_search_to_store_fk_map(cursor, table_name, col_name):
    q = f"""
    select a.id, b.id
    from ezidapp_search{table_name} a 
    join ezidapp_store{table_name} b on a.{col_name} = b.{col_name}
    order by a.id
    """
    cursor.execute(q, {})
    return {a: b for a, b in cursor.fetchall()}


def get_case_str(cursor, table_name, col_name):
    d = get_search_to_store_fk_map(cursor, table_name, col_name)
    return 'case ' + ' '.join(f'when {k} then {v}' for k, v in d.items()) + ' end'


@contextlib.contextmanager
def connect(db_name):
    log.info(f'Connecting to database: {db_name}')
    cnx = mysql.connector.connect(
        use_pure=False,
        pool_size=1,
        pool_name='mypool',
        host=DB_HOST,
        port=DB_PORT,
        user=DB_ROOT_USER,
        password=DB_ROOT_PW,
        database=db_name,
    )
    try:
        yield cnx
    finally:
        cnx.close()


if __name__ == '__main__':
    sys.exit(main())
