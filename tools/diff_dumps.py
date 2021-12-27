#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Compares two dump files

The dump files must be comparable: they
must both be raw dumps or both be normal dumps, must have the same
scope, etc.  In both files the records must be ordered by
identifier, as they are when produced by 'dump-store'.  (Dump files
produced by 'dump-binder' must be sorted first.

Reserved identifiers are not stored in the binder.

Usage:

   diff-dumps dump1 dump2

If a filename ends with ".gz", the dump is assumed to be
gzip-compressed.

This script requires an EZID module.  The PYTHONPATH environment
variable must include the .../SITE_ROOT/PROJECT_ROOT/impl directory;
if it doesn't, we attempt to dynamically locate it and add it.
"""


import gzip
import sys
import time

from impl import util


def formatTimestamp(t):
    if t is not None:
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(int(t)))
    else:
        return "none"


if len(sys.argv) != 3:
    sys.stderr.write("Usage: diff-dumps dump1 dump2\n")
    sys.exit(1)

if sys.argv[1].endswith(".gz"):
    fileA = gzip.GzipFile(filename=sys.argv[1], mode="r")
else:
    fileA = open(sys.argv[1])
if sys.argv[2].endswith(".gz"):
    fileB = gzip.GzipFile(filename=sys.argv[2], mode="r")
else:
    fileB = open(sys.argv[2])


def nextRecord(file):
    try:
        return util.fromExchange(next(file), identifierEmbedded=True)
    except StopIteration:
        return None, None


# noinspection PyTypeChecker
idA, recordA = nextRecord(fileA)
# noinspection PyTypeChecker
idB, recordB = nextRecord(fileB)
while idA is not None or idB is not None:
    if idA is not None and (idB is None or idA < idB):
        print("<", idA)
        # noinspection PyUnresolvedReferences,PyUnresolvedReferences
        print(
            f"\t< _created: {formatTimestamp(recordA.get('_created', recordA.get('_c')))}"
        )
        idA, recordA = nextRecord(fileA)
    elif idB is not None and (idA is None or idB < idA):
        print(">", idB)
        # noinspection PyUnresolvedReferences,PyUnresolvedReferences
        print(
            f"\t> _created: {formatTimestamp(recordB.get('_created', recordB.get('_c')))}"
        )
        idB, recordB = nextRecord(fileB)
    else:
        if recordA != recordB:
            print("!", idA)
            # noinspection PyUnresolvedReferences
            keysA = list(recordA.keys())
            keysA.sort()
            # noinspection PyUnresolvedReferences
            keysB = list(recordB.keys())
            keysB.sort()
            a = b = 0
            while a < len(keysA) or b < len(keysB):
                if a < len(keysA) and (b >= len(keysB) or keysA[a] < keysB[b]):
                    # noinspection PyUnresolvedReferences
                    print(
                        f"\t< {util.encode4(keysA[a])}: {util.encode3(recordA[keysA[a]])}"
                    )
                    a += 1
                elif b < len(keysB) and (a >= len(keysA) or keysB[b] < keysA[a]):
                    # noinspection PyUnresolvedReferences
                    print(
                        f"\t> {util.encode4(keysB[b])}: {util.encode3(recordB[keysB[b]])}"
                    )
                    b += 1
                else:
                    # noinspection PyUnresolvedReferences,PyUnresolvedReferences
                    if recordA[keysA[a]] != recordB[keysB[b]]:
                        if keysA[a] in ["_created", "_c", "_updated", "_u"]:
                            # noinspection PyUnresolvedReferences
                            print(
                                f"\t< {keysA[a]}: {formatTimestamp(recordA[keysA[a]])}"
                            )
                            # noinspection PyUnresolvedReferences
                            print(
                                f"\t> {keysB[b]}: {formatTimestamp(recordB[keysB[b]])}"
                            )
                        else:
                            # noinspection PyUnresolvedReferences
                            print(
                                f"\t< {util.encode4(keysA[a])}: {util.encode3(recordA[keysA[a]])}"
                            )
                            # noinspection PyUnresolvedReferences
                            print(
                                f"\t> {util.encode4(keysB[b])}: {util.encode3(recordB[keysB[b]])}"
                            )
                    a += 1
                    b += 1
        idA, recordA = nextRecord(fileA)
        idB, recordB = nextRecord(fileB)
