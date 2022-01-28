#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Compares identifiers in the store and search databases.

This script requires several EZID modules.  The PYTHONPATH environment variable must
include the .../SITE_ROOT/PROJECT_ROOT directory; if it doesn't, we attempt to
dynamically locate it and add it.  The DJANGO_SETTINGS_MODULE environment variable must
be set.
"""

import sys
import time

# import ezidapp.models
import ezidapp.models.identifier
from impl import util

if len(sys.argv) != 1:
    sys.stderr.write("Usage: diff-store-search\n")
    sys.exit(1)


def formatBoolean(b):
    return "yes" if b else "no"


def formatTimestamp(t):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t))


def harvest(model):
    lastId = ""
    while True:
        ids = (
            model.objects.filter(identifier__gt=lastId)
            .select_related("owner", "ownergroup", "datacenter", "profile")
            .order_by("identifier")[:1000]
        )
        if len(ids) == 0:
            break
        for id in ids:
            yield id
            lastId = id.identifier
    while True:
        yield None


# noinspection PyTypeChecker
storeIdentifiers = harvest(ezidapp.models.identifier.Identifier)
# noinspection PyTypeChecker
searchIdentifiers = harvest(ezidapp.models.identifier.Identifier)

stid = next(storeIdentifiers)
seid = next(searchIdentifiers)
while stid is not None or seid is not None:
    if stid is not None and (seid is None or stid.identifier < seid.identifier):
        if stid.owner is not None:
            print("<", stid.identifier)
            print(f"\t< createTime: {formatTimestamp(stid.createTime)}")
        stid = next(storeIdentifiers)
    elif seid is not None and (stid is None or seid.identifier < stid.identifier):
        print(">", seid.identifier)
        print(f"\t> createTime: {formatTimestamp(seid.createTime)}")
        seid = next(searchIdentifiers)
    else:
        firstDifference = [True]

        def compare(label, a, b):
            if a != b:
                if firstDifference[0]:
                    print("!", stid.identifier)
                    firstDifference[0] = False
                if a != "":
                    print(f"\t< {util.encode4(label)}: {util.encode3(a)}")
                if b != "":
                    print(f"\t> {util.encode4(label)}: {util.encode3(b)}")

        # noinspection PyUnresolvedReferences
        compare("owner", stid.owner.username, seid.owner.username)
        # noinspection PyUnresolvedReferences
        compare("ownergroup", stid.ownergroup.groupname, seid.ownergroup.groupname)
        # noinspection PyUnresolvedReferences
        compare(
            "createTime",
            formatTimestamp(stid.createTime),
            formatTimestamp(seid.createTime),
        )
        # noinspection PyUnresolvedReferences
        compare(
            "updateTime",
            formatTimestamp(stid.updateTime),
            formatTimestamp(seid.updateTime),
        )
        # noinspection PyUnresolvedReferences
        compare("status", stid.get_status_display(), seid.get_status_display())
        # noinspection PyUnresolvedReferences
        compare("unavailableReason", stid.unavailableReason, seid.unavailableReason)
        # noinspection PyUnresolvedReferences
        compare("exported", formatBoolean(stid.exported), formatBoolean(seid.exported))
        # noinspection PyUnresolvedReferences
        if stid.isDatacite:
            # noinspection PyUnresolvedReferences
            compare("datacenter", stid.datacenter.symbol, seid.datacenter.symbol)
        # noinspection PyUnresolvedReferences
        compare(
            "crossrefStatus",
            stid.get_crossrefStatus_display(),
            seid.get_crossrefStatus_display(),
        )
        # noinspection PyUnresolvedReferences
        compare("crossrefMessage", stid.crossrefMessage, seid.crossrefMessage)
        # noinspection PyUnresolvedReferences
        compare("target", stid.target, seid.target)
        # noinspection PyUnresolvedReferences
        compare("profile", stid.profile.label, seid.profile.label)
        # noinspection PyUnresolvedReferences
        compare("agentRole", stid.get_agentRole_display(), seid.get_agentRole_display())
        # noinspection PyUnresolvedReferences
        stKeys = sorted(stid.cm.keys())
        seKeys = sorted(seid.cm.keys())
        sti = sei = 0
        while sti < len(stKeys) or sei < len(seKeys):
            if sti < len(stKeys) and (sei >= len(seKeys) or stKeys[sti] < seKeys[sei]):
                # noinspection PyUnresolvedReferences
                compare("cm/" + stKeys[sti], stid.cm[stKeys[sti]], "")
                sti += 1
            elif sei < len(seKeys) and (
                sti >= len(stKeys) or seKeys[sei] < stKeys[sti]
            ):
                compare("cm/" + seKeys[sei], "", seid.cm[seKeys[sei]])
                sei += 1
            else:
                # noinspection PyUnresolvedReferences
                compare("cm/" + stKeys[sti], stid.cm[stKeys[sti]], seid.cm[seKeys[sei]])
                sti += 1
                sei += 1
        stid = next(storeIdentifiers)
        seid = next(searchIdentifiers)
