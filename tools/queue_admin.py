#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Queue administration tool

Currently works with the binder and DataCite queues only.  Run with the '-h' option for
usage.

This script requires several EZID modules.  The PYTHONPATH environment variable must
include the .../SITE_ROOT/PROJECT_ROOT directory; if it doesn't, we attempt to
dynamically locate it and add it.  The DJANGO_SETTINGS_MODULE environment variable must
be set.
"""

import argparse
import sys
import time

import django.db.models
import django.db.transaction

# import ezidapp.models
import ezidapp.models.async_queue
from impl import util

queue = None  # set below; the queue model class object manager


def formatTimestamp(t):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t))


def permanentErrors():
    return queue.filter(errorIsPermanent=True)


def transientErrors():
    return queue.filter(~django.db.models.Q(error="")).filter(errorIsPermanent=False)


def printOverview(_args):
    with django.db.transaction.atomic():
        l = queue.count()
        net = queue.aggregate(django.db.models.Min("enqueueTime"))["enqueueTime__min"]
        xet = queue.aggregate(django.db.models.Max("enqueueTime"))["enqueueTime__max"]
        pe = permanentErrors().count()
        te = transientErrors().count()
    print(f"entries: {l:d}")
    print(f"earliest: {'-' if net is None else formatTimestamp(net)}")
    print(f"latest: {'-' if xet is None else formatTimestamp(xet)}")
    print(f"permanent errors: {pe:d}")
    print(f"transient errors: {te:d}")


def listErrors(rows):
    errors = {}
    for r in list(rows):
        l = errors.get(r.error, [])
        l.append(r)
        errors[r.error] = l
    for e, l in list(errors.items()):
        print(util.oneLine(e))
        for r in l:
            print(
                f"   {r.seq:d} {formatTimestamp(r.enqueueTime)} {r.operation} {r.identifier}"
            )


def listPermanentErrors(_args):
    listErrors(permanentErrors().order_by("seq"))


def listTransientErrors(_args):
    listErrors(transientErrors().order_by("seq"))


def clearPermanentErrorFlags(_args):
    permanentErrors().update(errorIsPermanent=False)


def deleteEntries(args):
    for r in args.ranges:
        queue.filter(seq__range=r).delete()


def seqOrRangeType(arg):
    try:
        if "-" not in arg:
            arg = "%s-%s" % (arg, arg)
        l = tuple(int(v) for v in arg.split("-"))
        assert len(l) == 2 and l[0] <= l[1]
        return l
    except Exception:
        raise argparse.ArgumentTypeError("invalid seq or range of seqs")


p = argparse.ArgumentParser(description="Queue administration.")
p.add_argument("queue", choices=["binder", "datacite"], help="the queue to administer")
sp = p.add_subparsers(help="commands")
sp.add_parser("overview", help="print overview").set_defaults(func=printOverview)
sp.add_parser("list-perrors", help="list permanent errors").set_defaults(
    func=listPermanentErrors
)
sp.add_parser("list-terrors", help="list transient errors").set_defaults(
    func=listTransientErrors
)
sp.add_parser("clear-perrors", help="clear permanent error flags").set_defaults(
    func=clearPermanentErrorFlags
)
spp = sp.add_parser("delete", help="delete selected entries")
spp.set_defaults(func=deleteEntries)
spp.add_argument(
    "ranges",
    nargs="*",
    help="seq or range of seqs",
    metavar="seq[-seq]",
    type=seqOrRangeType,
)

args = p.parse_args(sys.argv[1:])
if args.queue == "binder":
    queue = ezidapp.models.async_queue.BinderQueue.objects
else:
    queue = ezidapp.models.async_queue.DataciteQueue.objects
args.func(args)
