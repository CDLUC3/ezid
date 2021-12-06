#!/usr/bin/env python

# Copyright©2021, Regents of the University of California
# http://creativecommons.org/licenses/BSD

"""Migrate EZID's various legacy blob formats to JSON.

The blobs are read from the cm field and stored in the metadata fields of the
ezidapp_searchidentifier and ezidapp_storeidentifier tables.
"""
import argparse
import ast
import base64
import contextlib
import functools
import json
import logging
import multiprocessing
import multiprocessing.managers
import multiprocessing.pool
import os
import sys
import time
import zlib

import mysql.connector
import mysql.connector.cursor


log = logging.getLogger(__name__)

BATCH_SIZE = 10_000


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('table', choices=['store', 'search'])
    args = parser.parse_args()

    try:
        conn_args = dict(
            host=os.environ['DB_HOST'],
            port=os.environ['DB_PORT'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PW'],
            database=os.environ['DB_NAME'],
        )
    except KeyError:
        raise AssertionError(
            "Must set environment variables: DB_HOST, DB_PORT, DB_USER, DB_PW, DB_NAME"
        )
    db = MigrateBlobsToMetadata(conn_args, table_str=args.table)
    db.run()


class MigrateBlobsToMetadata:
    def __init__(self, conn_args, table_str):
        # self.counter = impl.nog.counter.Counter(out_fn=log.info)
        # self.counter_lock = multiprocessing.RLock()
        self.page_size = 10_000
        self.start_ts = time.time()
        self.prev_ts = self.start_ts
        self.conn_args = conn_args
        self.table_str = table_str

    def run(self):
        pool = multiprocessing.pool.Pool(4 * multiprocessing.cpu_count())
        # pool = multiprocessing.pool.Pool(
        #     processes=2,
        # initializer=myinit,
        # initargs=self.conn_args,
        # )

        with connect(self.conn_args) as conn:
            # n.conn = conn

            cursor = conn.cursor()
            # cursor = conn.cursor()
            # conn.autocommit = False
            cursor.execute('set unique_checks = 0', {})
            cursor.execute('set foreign_key_checks = 0', {})

            last_id = 0

            while True:
                # Counter-intuitive syntax for processing in chunks
                q = f"""
                select id, cm from ezidapp_{self.table_str}identifier
                where id = last_insert_id(id)
                and id > {last_id}
                order by id
                limit {BATCH_SIZE}
                ;
                """
                print(f'id > {last_id}')
                print(q)
                cursor.execute(q, {})

                # cursor.fetchall()
                # for id, cm in cursor.fetchall():
                res = pool.map_async(
                    functools.partial(proc_blob, self.conn_args, self.table_str),
                    cursor.fetchall(),
                    100,
                )
                res.get()

                #     # metadata_json = metadata_json.replace("\\", '\\\\')
                #     # print(metadata_json)
                #     # pprint.pp(json.loads(metadata_json))

                q = """
                select last_insert_id();
                """
                cursor.execute(q, {})
                new_last_id = cursor.fetchone()[0]

                if new_last_id == last_id:
                    break

                last_id = new_last_id

                # conn.commit()
                # del cursor

                cur_ts = time.time()
                print(f'Batch: {cur_ts - self.prev_ts:.2f}s')
                self.prev_ts = cur_ts

        print(f'Total {time.time() - self.start_ts:.2f}s')


def proc_blob(conn_args, table_str, args):
    # print('#'*100)
    row_id, blob_bytes = args
    # print(conn_args, row_id, blob_bytes)

    if not hasattr(proc_blob, 'conn'):
        print('Connecting')
        proc_blob.conn = mysql.connector.connect(
            use_pure=False,
            **conn_args,
        )

    json_str, op_list = decode(blob_bytes)
    # JSON will be both validated and normalized by MySQL
    try:
        metadata_dict = json.loads(json_str)
    except json.decoder.JSONDecodeError:
        return

    # print(metadata_dict)

    proc_blob.conn.cursor().execute(
        f"""
    update ezidapp_{table_str}identifier
    set metadata = %s
    where id = %s
    """,
        (json.dumps(metadata_dict), row_id),
    )


@contextlib.contextmanager
def connect(conn_args):
    log.info(f'Connecting to database:')
    for k, v in conn_args.items():
        log.info(f'{k}: {v}')
    conn = mysql.connector.connect(
        use_pure=False,
        # pool_size=10,
        # pool_name='mypool',
        **conn_args,
    )
    log.info(f'Connected')
    try:
        yield conn
    # except Exception as e:
    #     log.error(f'Database connection failed: {str(e)}')
    #     sys.exit(1)
    finally:
        conn.close()


def decode(obj):
    """Decode all blob formats used in previous and current EZID"""
    op_list = []

    @contextlib.contextmanager
    def w(obj, op_str):
        # lib_util.log_obj(obj, msg=f'Before "{op_str}"')
        with contextlib.suppress(Exception):
            yield
            op_list.append(op_str)

    if not isinstance(obj, bytes):
        with w(obj, f'{obj.__class__.__name__}-to-bytes'):
            obj = to_bytes(obj)
    with w(obj, 'decompress'):
        obj = zlib.decompress(obj)
    with w(obj, 'bytes-to-str'):
        obj = obj.decode('utf-8', errors='replace')
    # with w(obj, 'decode'):
    #     obj = obj.decode('utf-8', errors='replace')
    with w(obj, 'from-base64'):
        obj = base64.b64decode(obj, validate=True)
    # with w(obj, 'from-json'):
    #     obj = next(django.core.serializers.deserialize("json", obj))
    with w(obj, 'from-python-str'):
        obj = ast.literal_eval(obj)
    if isinstance(obj, str):
        with w(obj, 'from-nested-python-str'):
            obj = ast.literal_eval(obj)
    with w(obj, 'from-json'):
        obj = json.loads(obj)
    op_list.append(f'to-{obj.__class__.__name__}')
    # if not isinstance(obj, dict):
    #     log.error(f'  FINAL : {type(obj)}: {obj!r}')
    json_str = json.dumps(obj)
    return json_str, op_list


def to_bytes(obj):
    if obj is None:
        return None
    elif isinstance(obj, bytes):
        return obj
    elif isinstance(obj, str):
        return obj.encode('utf-8', errors='replace')
    elif isinstance(obj, memoryview):
        return obj.tobytes()
    else:
        raise AssertionError(f'Unexpected type: {obj!r}')


if __name__ == '__main__':
    sys.exit(main())
