#!/usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Bin metadata JSON strings by size and pick one metadata element per bin

The selected metadata docs should be representative for what's in the database, and
usable for tests
"""

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import logging
import lzma
import math
import sys

LEN_CSV_PATH = './dev-len.csv.xz'
DECODED_CSV_PATH = './dev-decoded.csv.xz'

log = logging.getLogger(__name__)


def main():
    # perr('Finding longest blob...')
    # longest_len = max(row[2] for row in blob_len_gen())
    # perr(f'len_longest={longest_len}')

    # We want 100 sample blobs but selecting evenly distributed or random blobs causes
    # gives us a uniform type of metadata that is in most blobs above a certain size.
    # This instead creates bins that get larger on an exponential curve, giving us most
    # samples on the lower bin sizes. The magic value that we multiply with was selected by
    # hand so that the final bin would cover the longest blob.
    bin_tup = tuple(int(math.exp(i * 0.115)) for i in range(100))
    perr(f'bins={bin_tup}')
    for bin_min_int, bin_max_int in zip(bin_tup, bin_tup[1:]):
        perr(f'{bin_min_int} - {bin_max_int}')
        if bin_min_int == bin_max_int:
            continue
        for idx, row_id, len in blob_len_gen():
            if bin_min_int <= len < bin_max_int:
                blob = get_blob(row_id)
                print('\t'.join(map(str, (bin_min_int, row_id, len, blob))))
                break

def perr(*a, **kw):
    print(*a, **kw, file=sys.stderr)


def get_blob(row_id):
    for line in lzma.open(DECODED_CSV_PATH, mode='rt', encoding='utf-8'):
        line:str
        cur_row_id, blob_str = line.strip().split(',', 1)
        if int(cur_row_id) == row_id:
            return blob_str
    raise AssertionError(f'Invalid row_id: {row_id}')


def blob_len_gen():
    for i, line in enumerate(lzma.open(LEN_CSV_PATH, mode='rt', encoding='utf-8')):
        row_id, len_str = line.strip().split(',')
        len = int(len_str)
        yield i, int(row_id), int(len_str)


if __name__ == '__main__':
    sys.exit(main())
