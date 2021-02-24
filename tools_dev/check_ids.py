#!/usr/bin/env python

"""Annotate a stream of identifiers with associated metadata and misc
housekeeping information pulled from an EZID database.
"""

import argparse
import collections
import fileinput
import json
import logging
import pprint
import sys
import time
import zlib

import aiomysql
import asyncio
import configparser
import myloginpath

log = logging.getLogger(__name__)

DEFAULT_CONCURRENT_CONNECTIONS = 20

# CNF_PATH = "~/.my.cnf"

TABLE_NAME_TO_ORM = {
    "store": {"db": "ezidapp_storeidentifier", "orm": "StoreIdentifier"},
    "search": {"db": "ezidapp_searchidentifier", "orm": "SearchIdentifier"},
}

# CnfTup = collections.namedtuple(
#     "CnfTup", ["cnf_name", "connect_name", "default", "desc"], verbose=True
# )

# Map MySQL config file keys to aiohttp.connect() params
CONFIG_TO_CONNECT = {
    "host": "host",
    "port": "port",
    "user": "user",
    "password": "password",
    "db": "database",
}


async def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "login_path",
        metavar='NAME',
        help="Name of database credentials added with mysql_config_editor (see check-ids.md for more information)",
    )
    parser.add_argument(
        "--max-concurrent",
        "-m",
        type=int,
        default=DEFAULT_CONCURRENT_CONNECTIONS,
        help="Number of concurrent connections to the EZID database",
    )
    parser.add_argument(
        "files",
        metavar="FILE",
        nargs="*",
        help="Files containing identifiers to check",
    )
    parser.add_argument(
        "--debug",
        "-v",
        action="store_true",
        help="Enable debug level logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(levelname)-8s %(message)s",
    )

    asyncio.get_running_loop().set_debug(args.debug)

    try:
        check_identifiers = CheckIdentifiers(args)
        await check_identifiers.check_all()
    except LoginNotFound as e:
        log.error(repr(e))
        return 1
    except CheckIdentifiersError as e:
        log.error(repr(e))
        if args.debug:
            raise


class CheckIdentifiers:
    def __init__(self, args):
        self.args = args
        self.login_dict = None
        self.queue = None

    async def check_all(
        self,
    ):
        self.login_dict = self.get_mysql_login(self.args.login_path)
        start_ts = time.time()
        self.queue = asyncio.Queue(maxsize=3)
        worker_list = []

        for _ in range(self.args.max_concurrent):
            worker_list.append(asyncio.create_task(self.worker()))

        try:
            async for id_str in self.id_gen():
                await self.queue.put(id_str)
        finally:
            await self.queue.join()
            for worker in worker_list:
                worker.cancel()
            result_list = await asyncio.gather(*worker_list, return_exceptions=True)
            for result in result_list:
                if result is None:
                    continue
                elif isinstance(result, asyncio.CancelledError):
                    # CancelledError is not an error...
                    continue
                log.info(repr(result))

        elapsed_ts = time.time() - start_ts
        min_float, sec_float = divmod(elapsed_ts, 60)

        log.info(f"Elapsed: {round(min_float)} min {round(sec_float)} sec")

    async def check(self, cur, id_str):
        if not id_str:
            count(id_str, "Empty identifier")
            return

        for table_key, table_dict in list(TABLE_NAME_TO_ORM.items()):
            db_str, orm_str = table_dict["db"], table_dict["orm"]
            await self.check_identifier(cur, id_str, db_str, orm_str)
            count(id_str, "Identifiers checked")

    async def check_identifier(self, cur, id_str, db_str, orm_str):
        # noinspection SqlResolve
        q = f"""
            select *
            from {db_str} es
            where identifier = %s
        """
        await cur.execute(q, (id_str,))
        result = await cur.fetchone()
        if result is None:
            count(id_str, f"Object missing in {orm_str}")
            return

        meta_dict = json.loads(zlib.decompress(result["cm"]))
        if not meta_dict:
            count(id_str, f"No metadata record found in {orm_str}")
        else:
            count(
                id_str,
                f"Metadata record found in {orm_str}",
                meta_dict,
            )

    async def id_gen(
        self,
    ):
        for id_str in fileinput.input(self.args.files):
            id_str = id_str.strip()
            log.info(f"Yield: {id_str}")
            yield id_str.strip()

    async def worker(self):
        while True:
            async with (await self.connect()).cursor() as cur:
                while True:
                    id_str = None
                    try:
                        id_str = await self.queue.get()
                        await self.check(cur, id_str)

                    except (asyncio.CancelledError, KeyboardInterrupt):
                        raise asyncio.CancelledError()

                    except CheckIdentifiersError as e:
                        log.error(repr(e))
                        #
                        break

                    except Exception as e:
                        if "IncompleteReadError" in repr(e):
                            # For some reason KeyboardInterrupt arrives as
                            # "AttributeError("module 'asyncio.streams' has no attribute
                            # 'IncompleteReadError'" here. Must be a bug in aiomysql.
                            raise asyncio.CancelledError(repr(e))

                        msg_str = f"Exception in worker: {repr(e)}"
                        log.error(msg_str)
                        count(id_str, msg_str)
                        # Create a new connection, just in case the exception was caused by a
                        # network error.
                        break

                    finally:
                        if id_str is not None:
                            self.queue.task_done()

    async def connect(self):
        try:
            c = await aiomysql.connect(
                read_default_file=False,
                charset="utf8mb4",
                cursorclass=aiomysql.cursors.DictCursor,
                loop=asyncio.get_event_loop(),
                **self.login_dict,
            )
            return c
        except aiomysql.Error as e:
            log.error(f"Unable to connect to MySQL: {repr(e)}")

    def get_mysql_login(self, login_path):
        try:
            login_dict = myloginpath.parse(login_path)
        except (configparser.Error, KeyError, TypeError) as e:
            raise LoginNotFound(
                'Unable to get MySQL connection string for "{}". Error: {}'.format(
                    login_path, repr(e)
                )
            )
        login_dict = {
            **{CONFIG_TO_CONNECT.get(k, k): v for k, v in list(login_dict.items())},
            'db': login_path,
        }
        self.log_kv(
            f'Found MySQL login for "{login_path}"', {**login_dict, "pw": "***"}
        )
        return login_dict

    def log_kv(self, title_str, d, log_fn=log.info):
        log_fn(f'{title_str}:')
        [log_fn(f'  {k}: {v}') for k, v in list({**d, "pw": "***"}.items())]

    def log_pp(self, title_str, d, log_fn=log.info):
        log_fn(f'{title_str}:')
        [log_fn(f'  {line}') for line in pprint.pformat(d).splitlines(keepends=False)]


class CheckIdentifiersError(Exception):
    pass


class LoginNotFound(CheckIdentifiersError):
    pass


class Counter:
    def __init__(self):
        self.count_dict = collections.defaultdict(lambda: 0)
        self.last_msg_ts = None

    def __enter__(self):
        self.last_msg_ts = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("-" * 100)
        self.print_counters()

    def count(self, id_str, key, detail_obj=None):
        self.count_dict[key] += 1
        if detail_obj is None:
            pass
        elif isinstance(detail_obj, str):
            log.info(f"{id_str}: {key}: {detail_obj}")
        else:
            self.log_pp(f'{id_str}: {key}:', detail_obj)
        if time.time() - self.last_msg_ts >= 1.0:
            self.last_msg_ts = time.time()
            self.print_counters()

    def log_pp(self, title_str, obj, log_fn=log.info):
        log_fn(title_str)
        [log_fn(f'  {s}') for s in pprint.pformat(obj).splitlines(keepends=False)]

    def print_counters(self):
        if not self.count_dict:
            log.info("No checks counted yet...")
            return
        log.info("Counters:")
        for k, v in sorted(self.count_dict.items()):
            log.info(f"  {v:>5,}: {k}")


counter = Counter()
count = counter.count

if __name__ == "__main__":
    with counter:
        sys.exit(asyncio.run(main()))
