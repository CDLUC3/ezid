import collections
import logging
import pprint
import time

log = logging.getLogger(__name__)


class Counter:
    def __init__(self, out_fn=log.info):
        self.count_dict = collections.defaultdict(lambda: 0)
        self.last_msg_ts = None
        self.out_fn = out_fn

    def __enter__(self):
        self.last_msg_ts = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.out_fn("-" * 100)
        self.print_counters()

    def count(self, id_str, key, detail_obj=None, delta_int=1):
        self.count_dict[key] += delta_int
        if detail_obj is None:
            pass
        elif isinstance(detail_obj, str):
            self.p(f"{id_str}: {key}: {detail_obj}")
        else:
            self.pp(f'{id_str}: {key}:', detail_obj)
        if time.time() - self.last_msg_ts >= 1.0:
            self.last_msg_ts = time.time()
            self.print_counters()

    def print_counters(self):
        if not self.count_dict:
            self.p("No checks counted yet...")
            return
        self.p("Counters:")
        for k, v in sorted(self.count_dict.items()):
            self.p(f"  {v:>5,}: {k}")

    def pp(self, title_str, obj):
        self.p(title_str)
        [
            self.p(f'  {s}')
            for s in pprint.pformat(obj).splitlines(keepends=False)
        ]

    def p(self, s):
        self.out_fn(s)
