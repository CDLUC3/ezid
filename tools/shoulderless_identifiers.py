#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

# Finds and counts all shoulderless identifiers, i.e., identifiers
# that are not extensions of current shoulders.  The identifiers are
# grouped by owner and shoulder (well, since the identifiers are
# shoulderless, their former shoulders are inferred; see
# util.inferredShoulder).  A CSV file with three columns is written to
# standard output: owner, shoulder, and identifier count.
#
# This script requires several EZID modules.  The PYTHONPATH
# environment variable must include the .../SITE_ROOT/PROJECT_ROOT
# directory; if it doesn't, we attempt to dynamically locate it and
# add it.  The DJANGO_SETTINGS_MODULE environment variable must be
# set.
#
# Greg Janee <gjanee@ucop.edu>
# June 2019

# @executable

import csv
import sys

# import ezidapp.models
import ezidapp.models.shoulder
import ezidapp.models.identifier
from impl import util

shoulders = [s.prefix for s in ezidapp.models.shoulder.Shoulder.objects.all()]

orphans = {}  # username: { shoulder: count }

lastIdentifier = ""
while True:
    qs = (
        ezidapp.models.identifier.Identifier.objects.filter(
            identifier__gt=lastIdentifier
        )
        .order_by("identifier")
        .select_related("owner")
    )
    qs = list(qs[:1000])
    if len(qs) == 0:
        break
    for si in qs:
        if not any(si.identifier.startswith(s) for s in shoulders):
            s = util.inferredShoulder(si.identifier)
            u = orphans.get(si.owner.username, {})
            u[s] = u.get(s, 0) + 1
            orphans[si.owner.username] = u
    lastIdentifier = qs[-1].identifier

w = csv.writer(sys.stdout)

for u in sorted(orphans.keys()):
    for s in sorted(orphans[u].keys()):
        w.writerow([u, s, str(orphans[u][s])])
