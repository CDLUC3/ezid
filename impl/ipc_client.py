#!/usr/bin/env python

"""
An IPC client that stress tests the shared objects.

Start instances of the client to create processes, specify number of threads to create
multiple threads for the process, and specify loops to create work for the processes.

Each loop increases the value for a random key by one. If everything works as expected,
the sum of the values after all loops are completed by all processes, should match
the number of `processes * threads * loops`.
"""

# named_thread_locks = impl.ipc.NamedThreadLocks()
# impl.ipc.threading_lock = threading.RLock()

import argparse
import logging
import os
import random
import sys
import threading
import time

import impl.ipc

# MAX_LOCKED_IDENTIFIERS = 1024
# MAX_ACTIVE_USERS = 1024
# MAX_WAITING_USERS = 1024
# PAUSE_FLAG_SIZE = 4

DEFAULT_MAX_ITEM_COUNT = 100
DEFAULT_LOOP_COUNT = 10000

a_resource_lock = impl.ipc.CombinedLock()

log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'name',
        nargs='?',
        default='shared_memory',
        help='Shared name for a group of processes and threads sharing resources',
    )
    parser.add_argument(
        '--tag',
        default='proc-0',
        action='store',
        help='Provde a tag for the process',
    )
    parser.add_argument(
        '--loop',
        default=DEFAULT_LOOP_COUNT,
        action='store',
        type=int,
        help='Set number of loops in the test',
    )
    parser.add_argument(
        '--max-items',
        default=DEFAULT_MAX_ITEM_COUNT,
        action='store',
        type=int,
        help='Max number of key/value pairs in the shared dict',
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Debug level logging',
    )
    args = parser.parse_args()

    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)-8s %(message)s',
        stream=sys.stderr,
    )

    # logging.root.handlers.clear()
    logging.getLogger('tracer').setLevel(level)

    log = ProcAdapter(
        logging.getLogger(__name__),
        {
            'tag': args.tag,
            'pid': os.getpid(),
            'tid': threading.get_native_id(),
        },
    )

    mm = impl.ipc.MemMapDict(args.name, args.max_items, 'i')

    start_ts = time.time()
    print_ts = time.time()
    get_total = 0
    adjust_total = 0

    for j in range(args.loop):
        if time.time() - print_ts > 1.0:
            log.info(f'get_total: {get_total}')
            log.info(f'adjust_total: {adjust_total}')
            print_ts = time.time()

        r = random.randint(0, 99)
        with mm as x:
            x.adjust(r, 1)
            adjust_total += 1

    log.info(f'Target total: {adjust_total}')

    while True:
        check_total = 0
        with mm as x:
            for i in range(args.max_items):
                check_total += x.get(i, 0)

        log.info(f'#### {args.tag} {check_total}')

        time.sleep(5)

    # if args.tag != 'proc-0':
    #     log.info(f'Holding: {args.tag}')
    #     while True:
    #         pass
    #
    # while True:
    #     check_total = 0
    #     with mm as x:
    #         for i in range(args.max_items):
    #             check_total += x.get(i, 0)
    #     log.error(f'Check total: {args.tag}: {check_total}')
    #     while True:
    #         pass
    #
    # # check_total = 0
    # # with mm as x:
    # #     for i in range(args.max_items):
    # #         check_total += x.get(i, 0)
    # #
    # # log.error('#' * 100)
    # # log.error(f'Check total: {check_total}')
    # # log.error('#' * 100)
    # #
    # # while True:
    # #     log.info(f'Check total fromm : {args.tag}')
    # #     time.sleep(3)


class ProcAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        # Add tag, process id and thread it to log messages. The tag is just
        # included in log messages and otherwise not used.
        return (
            'tag/pid/tid=%s/%s/%s %s'
            % (self.extra['tag'], self.extra['pid'], self.extra['tid'], msg),
            kwargs,
        )


if __name__ == '__main__':
    sys.exit(main())
