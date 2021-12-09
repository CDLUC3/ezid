#!/usr/bin/env python

# Copyright©2021, Regents of the University of California
# http://creativecommons.org/licenses/BSD

"""\
Translate the foreign keys in the ezidapp_searchidentifier to match those in
ezidapp_storeidentifier.

Doing this in small batches is much faster than running a single query, probably because the
smaller transactions fit in memory. Large transactions are spilled to disk.
"""

import contextlib
import logging
import os
import sys
import time

import mysql.connector
import mysql.connector.cursor

log = logging.getLogger(__name__)

# Number of rows to update in each query
BATCH_SIZE = 10000


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)-8s %(message)s',
    )

    try:
        host_str = os.environ['DB_HOST']
        port_str = os.environ['DB_PORT']
        user_str = os.environ['DB_USER']
        pw_str = os.environ['DB_PW']
        name_str = os.environ['DB_NAME']
    except KeyError:
        raise AssertionError(
            "Must set environment variables: DB_HOST, DB_PORT, DB_USER, DB_PW, DB_NAME"
        )

    start_ts = time.time()
    prev_ts = start_ts

    with connect(host_str, port_str, user_str, pw_str, name_str) as conn:
        cursor = conn.cursor()

        owner_case_str = get_case_str(cursor, 'user', 'pid')
        group_case_str = get_case_str(cursor, 'group', 'pid')
        profile_case_str = get_case_str(cursor, 'profile', 'label')
        datacenter_case_str = get_case_str(cursor, 'datacenter', 'symbol')

        last_id = 0

        while True:
            cursor = conn.cursor()

            conn.autocommit = False

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

            q = """
            select last_insert_id();
            """
            cursor.execute(q, {})
            new_last_id = cursor.fetchone()[0]

            if new_last_id == last_id:
                break

            last_id = new_last_id

            conn.commit()
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
def connect(host_str, port_str, user_str, pw_str, name_str):
    log.info(f'Connecting to database:')
    for parm in 'host', 'port', 'user', 'name':
        log.info(f'{parm}: {locals()[parm + "_str"]}')
    conn = mysql.connector.connect(
        host=host_str,
        port=port_str,
        user=user_str,
        password=pw_str,
        database=name_str,
        use_pure=False,
        pool_size=1,
        pool_name='mypool',
    )
    log.info(f'Connected')
    try:
        yield conn
    except Exception as e:
        log.error(f'Database connection failed: {str(e)}')
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
