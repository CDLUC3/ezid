import collections
import logging
import pprint
import time

log = logging.getLogger(__name__)


class Counter:
    def __init__(self):
        self.count_dict = collections.defaultdict(lambda: 0)
        self.last_msg_ts = None

    def __enter__(self):
        self.last_msg_ts = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        log.info("-" * 100)
        self.print_counters(log.info)

    def count(self, id_str, key, detail_obj=None):
        self.count_dict[key] += 1
        if detail_obj is None:
            pass
        elif isinstance(detail_obj, str):
            self.p(f"{id_str}: {key}: {detail_obj}")
        else:
            self.pp(f'{id_str}: {key}:', detail_obj)
        if time.time() - self.last_msg_ts >= 1.0:
            self.last_msg_ts = time.time()
            self.print_counters(log.info)

    def print_counters(self, print_func):
        if not self.count_dict:
            print_func("No checks counted yet...")
            return
        print_func("Counters:")
        for k, v in sorted(self.count_dict.items()):
            print_func(f"  {v:>5,}: {k}")

    def pp(self, title_str, obj, print_func=None):
        self.p(title_str, print_func)
        [self.p(f'  {s}', print_func) for s in pprint.pformat(obj).splitlines(keepends=False)]

    def p(self, s, print_func=None):
        (print_func or log.debug)(s)

