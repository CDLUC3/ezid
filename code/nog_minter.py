#!/usr/bin/env python2

"""N2T EggNog compatible minter for EZID

Terminology:

- Sping: Semi-opaque string. E.g., '77913/r7006t'
- Minter: Sping generator
- Shoulder: Unique part of the sping. E.g., '77913/r7'
- Expandable template: The form of the minted spings. E.g., '77913/r7{eedk}'
- Mask: Format specifier for the generated part of the sping. E.g., 'eedk'
- Type: Always 'rand', designating pseudo-random sequence of spings (as opposed to
  sequential)
- DIG: Extended Digit. The alphabet used in the generated identifiers.

BerkeleyDB keys:

- saclist: List of active subcounters
- siclist: List of inactive (exhausted) subcounters
- top: Max allowed value of subcounter
- oacounter: Combined value of all subcounters
- oatop: Max allowed value for sum total of subcounter values
- atlast: Action to perform when template is exhausted. Always 'add3' for EZID,
  designating that template is expanded by repeating the first 3 characters. E.g.,
  'eedk' -> 'eedeedk' -> 'eedeedeedk'.
"""

# noinspection PyCompatibility
from __future__ import absolute_import, division, print_function

import argparse
import logging
import os
import pprint
import re
import sys

# A 3rd-party implementation of pathlib is available for Python 2.7 but it doesn't
# behave in quite the same way, so we'll use os.path until we move to Py3.
# import pathlib

try:
    import bsddb
except ImportError:
    # noinspection PyUnresolvedReferences
    import bsddb3 as bsddb

# fmt:off
XDIG_DICT = {
    # digits
    "0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    # chars
    "b": 10, "c": 11, "d": 12, "f": 13, "g": 14, "h": 15, "j": 16, "k": 17, "m": 18,
    "n": 19, "p": 20, "q": 21, "r": 22, "s": 23, "t": 24, "v": 25, "w": 26, "x": 27,
    "z": 28,
}
# fmt:on
XDIG_STR = "0123456789bcdfghjkmnpqrstvwxz"
ALPHA_COUNT = len(XDIG_STR)
DIGIT_COUNT = 10
COUNTER_COUNT = 290
# MINDERS_PATH = pathlib.Path("~/.minders").expanduser().resolve()
MINDERS_PATH = os.path.abspath(os.path.expanduser("~/.minders"))


log = logging.getLogger(__name__)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s %(levelname)9s %(message)s",
        stream=sys.stdout,
    )

    args = parse_command_line_args()

    if args.debug:
        logging.getLogger("").setLevel(logging.DEBUG)

    if args.dump:
        with _Bdb(args.naan_str, args.shoulder_str, dry_run=True) as bdb:
            bdb.dump()
        return

    for i, id_str in enumerate(
        mint(args.naan_str, args.shoulder_str, args.mint_count, args.dry_run)
    ):
        # log.info("{: 10d} {}".format(i + 1, id_str))
        print(id_str)


def parse_command_line_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description=__doc__
    )
    parser.add_argument("naan_str", metavar="naan")
    parser.add_argument("shoulder_str", metavar="shoulder")
    parser.add_argument(
        "--mint_count",
        "-c",
        metavar="mint-count",
        type=int,
        default=1,
        help="Number of spings to mint",
    )
    parser.add_argument(
        "--dump", "-d", action="store_true", help="Dump the minder BerkeleyDB and exit"
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Do not update the minder BerkeleyDB",
    )
    parser.add_argument(
        "--debug", "-g", action="store_true", help="Debug level logging",
    )
    return parser.parse_args()


def mint(naan_str, shoulder_str, mint_count=1, dry_run=False):
    """Generate ids with the given minter.

    Unless {dry_run} is set, the BerkeleyDB is updated to reflect the new state of the
    minder after successfully minting the requested number of spings.

    If the minter is interrupted before completing the minting, the database is not
    updated. This reflects the way N2T Nog operates.

    Args:
        naan_str (str):
        shoulder_str (str):
        mint_count (int): Number of spings to yield
        dry_run (bool): Don't update the minder BerkeleyDB after completed minting
    """
    with _Bdb(naan_str, shoulder_str, dry_run) as bdb:
        total_count = bdb.get_int("oacounter")
        max_total_count = bdb.get_int("oatop")
        assert (
            total_count <= max_total_count
        ), "Invalid subcounter total sum. total={} max={}".format(
            total_count, max_total_count
        )

        mask_str = bdb.get("mask")
        per_counter = bdb.get_int("percounter")

        assert re.match(r"[def]+k?$", mask_str), "Invalid mask_str: {}".format(mask_str)

        counter_key_list = _get_active_counter_list(bdb)

        for i in range(mint_count):
            # log.debug("percounter={}".format(per_counter))

            if total_count == max_total_count:
                log.info("Extending template. total={}".format(total_count))

                mask_str = _extend_template(mask_str, bdb.get("atlast"))
                bdb.set("mask", mask_str)
                # We don't use :/template but update it so that it matches for testing.
                bdb.set("template", "{}/{}".format(naan_str, shoulder_str))
                max_total_count = _get_max_count(mask_str)
                bdb.set("oatop", max_total_count)
                max_single_count = max_total_count // COUNTER_COUNT + 1
                _set_counter_max_values(bdb, max_single_count)

            counter_idx_and_value = _next(bdb, counter_key_list, per_counter,
                                          total_count)

            counter_key_list = _get_active_counter_list(bdb)

            total_count += 1

            s = _get_xdig_str(counter_idx_and_value, mask_str)
            id_str = "{}/{}{}".format(naan_str, shoulder_str, s)

            if mask_str.endswith("k"):
                id_str += _get_check_char(id_str)

            yield id_str

        if not dry_run:
            bdb.set("oacounter", total_count)


def _next(bdb, counter_key_list, per_counter, total_count):
    """Step the BerkeleyDB minder to the next state and return compounded counter index
    and value to use for the next sping.

    Exhausted counters are removed from counter_key_list.
    """
    rnd = _Drand48(total_count)
    counter_idx = int(rnd.drand() * len(counter_key_list))
    counter_name = counter_key_list[counter_idx]
    counter_idx = int(counter_name[1:])
    counter_key = "{}/value".format(counter_name)
    counter_int = bdb.get_int(counter_key) + 1
    bdb.set(counter_key, counter_int)
    n = counter_int + counter_idx * per_counter

    # log.debug(
    #     "counter_idx={} counter_name={} counter_int={} n={}".format(
    #         counter_idx, counter_name, counter_int, n
    #     )
    # )

    # Handle exhausted counter
    max_int = bdb.get_int("{}/top".format(counter_name))
    assert counter_int <= max_int, "Invalid counter value. counter={} max={}".format(
        counter_int, max_int
    )
    if counter_int == max_int:
        _deactivate_exhausted_counter(bdb, counter_idx)

    return n


def _deactivate_exhausted_counter(bdb, counter_idx):
    counter_name = bdb.list_pop("saclist", counter_idx)
    bdb.list_append("siclist", counter_name)


def _get_active_counter_list(bdb):
    active_list = bdb.get_list("saclist")
    # log.debug("active_list: {}".format(active_list))
    if not active_list:
        _reset_active_counter_list(bdb)
        _reset_exhausted_counter_list(bdb)
        return _get_active_counter_list(bdb)
    return active_list


def _reset_active_counter_list(bdb):
    """Activate all counters"""
    active_list = " ".join(_counter_names())
    bdb.set("saclist", active_list)


def _counter_names():
    return ("c{}".format(i) for i in range(COUNTER_COUNT))


def _set_counter_max_values(bdb, max_single_count):
    """Set the max (top) value for each counter"""
    for counter_name in _counter_names():
        bdb.set("{}/top".format(counter_name), max_single_count)


def _reset_exhausted_counter_list(bdb):
    """Clear list of exhausted counters"""
    bdb.set("siclist", "")


def _get_xdig_str(comp_counter, mask_str):
    """Convert compounded counter value to final sping as specified by the mask"""
    s = []

    for c in reversed(mask_str):
        if c == "k":
            continue
        elif c in ("e", "f"):
            divider = ALPHA_COUNT
        elif c == "d":
            divider = DIGIT_COUNT

        # noinspection PyUnboundLocalVariable
        # log.debug((comp_counter, divider))
        comp_counter, rem = divmod(comp_counter, divider)
        x_char = XDIG_STR[rem]

        if c == "f" and x_char.isdigit():
            return ""

        s.append(x_char)

    return "".join(reversed(s))


def _get_check_char(id_str):
    total_int = 0
    for i, c in enumerate(id_str):
        total_int += (i + 1) * XDIG_DICT.get(c, 0)
    return XDIG_STR[total_int % ALPHA_COUNT]


def _get_max_count(mask_str):
    """Calculate the max number of spings that can be generated with a given mask.
    """
    max_count = 1
    for c in mask_str:
        if c == "k":
            continue
        elif c in ("e", "f"):
            max_count *= ALPHA_COUNT
        elif c == "d":
            max_count *= DIGIT_COUNT
    return max_count


def _extend_template(mask_str, extend_str):
    m = re.match(r"add(\d)", extend_str)
    assert m, "Extend format must be string on form: add<digit>"
    add_int = int(m.group(1))
    return mask_str[:add_int] + mask_str


class _Bdb:
    def __init__(self, naan_str, shoulder_str, dry_run):
        self._dry_run = dry_run
        # bdb_path = MINDERS_PATH / pathlib.Path(naan_str, shoulder_str, "nog.bdb")
        bdb_path = os.path.join(MINDERS_PATH, naan_str, shoulder_str, "nog.bdb")
        log.debug("Minter BerkeleyDB: {}".format(bdb_path))
        # dry_run
        self.__bdb = bsddb.btopen(bdb_path, "rw")
        # self.__bdb = bsddb.btopen(bdb_path, "r" if dry_run else 'w')
        self._bdb = dict(self.__bdb)
        self._exit = False

    def __enter__(self):
        self._exit = False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._dry_run:
            self.__bdb.update(self._bdb)
        self._exit = True

    def __del__(self):
        assert self._exit, "Bdb destroyed without exiting context"
        if not self._dry_run:
            self.__bdb.update(self._bdb)

    def get(self, key_str):
        # return self._bdb[self._key(key_str)].decode("ascii") # Py3
        v = self._bdb[self._key(key_str)]
        log.debug("BDB: {} -> {}".format(key_str, v))
        return v

    def get_int(self, key_str):
        return int(self.get(key_str))

    def get_list(self, key_str):
        """Read a space separated list"""
        return self.get(key_str).split()

    def set(self, key_str, value):
        # self._bdb[self._key(key_str)] = str(value).encode("ascii") # Py3
        v = str(value)
        log.debug("BDB: {} <- {}".format(key_str, v))
        self._bdb[self._key(key_str)] = v

    def list_set(self, key_str, value_list):
        """Write a space separated list"""
        self.set(key_str, " ".join(value_list) + " ")

    def list_append(self, key_str, append_str):
        """Append to space separated list.
        """
        # Adds space at start like N2T does, for byte by byte comparison with N2T minter
        # state in tests.
        self.set(key_str, "{} {}".format(self.get(key_str), append_str))

    def list_pop(self, key_str, idx):
        """Pop from space separated list"""
        lst = self.get_list(key_str)
        s = lst.pop(idx)
        self.list_set(key_str, lst)
        return s

    def dump(self):
        """Dump the minder BerkeleyDB"""
        pprint.pprint(dict(self._bdb), indent=2)

    @staticmethod
    def _key(key_str):
        # return f":/{key_str}".encode("ascii") # Py3
        return ":/{}".format(key_str)


class _Drand48:
    """48-bit linear congruential PRNG, matching srand48() and drand48() in glibc."""

    def __init__(self, seed):
        # log.debug('seed={}'.format(seed))
        self.state = (seed << 16) + 0x330E

    def drand(self):
        self.state = (25214903917 * self.state + 11) & (2 ** 48 - 1)
        rnd = self.state / 2 ** 48
        # log.debug('rnd={}'.format(rnd))
        return rnd


def get_split_logger(name_str):
    """Return a logger that writes INFO level logs to stdout and remaining to stderr."""

    def mk_handler(is_info):
        class InfoFilter(logging.Filter):
            # def __init__(self, is_info):
            #     self._is_info = is_info
            #     super(InfoFilter, self).__init__()
            #
            def filter(self, rec):
                if is_info:
                    return rec.levelno == logging.INFO
                else:
                    return rec.levelno != logging.INFO

        stream = sys.stdout if is_info else sys.stderr
        h = logging.StreamHandler(stream)
        h.addFilter(InfoFilter())
        # h.setLevel(logging.DEBUG)
        return h

    logger = logging.getLogger(name_str)
    logger.setLevel(logging.DEBUG)

    logger.addHandler(mk_handler(False))
    logger.addHandler(mk_handler(True))

    return logger


if __name__ == "__main__":
    main()
