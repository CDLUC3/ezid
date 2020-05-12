#!/usr/bin/env python2
# -*- coding: future_fstrings -*-
##!/usr/bin/env python3.8

from __future__ import absolute_import, division, print_function

import argparse
import errno
import logging
import os
import pprint
import shutil

try:
    import bsddb
except ImportError:
    import bsddb3 as bsddb

MINDERS_PATH = os.path.abspath(os.path.expanduser("~/.minders"))
MINDERS_BACKUP_PATH = os.path.abspath(os.path.expanduser("~/minders-backup"))
TEST_DOCS_PATH = os.path.join(os.path.dirname(__file__), 'tests', 'test_docs')

log = logging.getLogger(__name__)


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(name)s %(levelname)9s %(message)s",
        # stream=sys.stdout,
    )

    args = parse_command_line_args()

    if args.action_str == "backup":
        return backup(args.naan_str, args.shoulder_str)
    elif args.action_str == "restore":
        return restore(args.naan_str, args.shoulder_str)
    elif args.action_str == "install":
        return install(args.naan_str, args.shoulder_str)
    elif args.action_str == "dump":
        return dump(args.naan_str, args.shoulder_str)
    else:
        assert False, 'Invalid action. Check ArgParser choices. action="{}"'.format(
            args.action_str
        )


def parse_command_line_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description=__doc__
    )
    parser.add_argument("action_str", choices=("dump", "backup", "restore"))
    parser.add_argument("naan_str", metavar="naan")
    parser.add_argument("shoulder_str", metavar="shoulder")
    return parser.parse_args()


def dump(naan_str, shoulder_str):
    """Dump the minder BerkeleyDB."""
    bdb_path = get_bdb_path(naan_str, shoulder_str)
    bdb = bsddb.btopen(bdb_path, "rw")
    pprint.pprint(dict(bdb), indent=2)


def backup(naan_str, shoulder_str):
    src_path = get_bdb_path(naan_str, shoulder_str)
    dst_path = get_bdb_backup_path(naan_str, shoulder_str)
    copy_file(src_path, dst_path)


def restore(naan_str, shoulder_str):
    src_path = get_bdb_backup_path(naan_str, shoulder_str)
    dst_path = get_bdb_path(naan_str, shoulder_str)
    copy_file(src_path, dst_path)


def install(naan_str, shoulder_str):
    src_path = get_test_docs_path(naan_str, shoulder_str)
    dst_path = get_bdb_path(naan_str, shoulder_str)
    copy_file(src_path, dst_path)


def copy_file(src_path, dst_path):
    mkdir_p(dst_path)
    shutil.copy(src_path, dst_path)


def get_bdb_path(naan_str, shoulder_str):
    return os.path.join(MINDERS_PATH, naan_str, shoulder_str, "nog.bdb")


def get_bdb_backup_path(naan_str, shoulder_str):
    return os.path.join(
        MINDERS_BACKUP_PATH, "{}_{}_nog.bdb".format(naan_str, shoulder_str)
    )


def get_test_docs_path(naan_str, shoulder_str):
    return os.path.join(
        TEST_DOCS_PATH, "{}_{}_nog.bdb".format(naan_str, shoulder_str)
    )


def mkdir_p(file_path):
    try:
        os.makedirs(os.path.dirname(file_path))
    except OSError as e:
        if not (e.errno == errno.EEXIST and os.path.isdir(file_path)):
            raise


if __name__ == "__main__":
    main()
