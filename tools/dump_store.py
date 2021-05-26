#! /usr/bin/env python

# Dumps the store database to standard output.
#
# Usage: dump-store [-erz]
#
# Options:
#   -e exclude reserved identifiers
#   -r raw dump
#   -z gzip the output
#
# This script requires several EZID modules.  The PYTHONPATH
# environment variable must include the .../SITE_ROOT/PROJECT_ROOT
# directory; if it doesn't, we attempt to dynamically locate it and
# add it.  The DJANGO_SETTINGS_MODULE environment variable must be
# set.
#
# Greg Janee <gjanee@ucop.edu>
# April 2013

import gzip
import optparse
import sys

import ezidapp.models.model_util
import ezidapp.models.identifier

# from impl import ezidapp.models
from impl import util

p = optparse.OptionParser(usage="%prog [-rz]")
p.add_option(
    "-e",
    action="store_true",
    dest="excludeReserved",
    default=False,
    help="exclude reserved identifiers",
)
p.add_option(
    "-r", action="store_true", dest="rawOutput", default=False, help="raw dump"
)
p.add_option(
    "-z", action="store_true", dest="gzipOutput", default=False, help="gzip output"
)
options, args = p.parse_args()
if len(args) != 0:
    p.error("wrong number of arguments")

if options.gzipOutput:
    outfile = gzip.GzipFile(fileobj=sys.stdout, mode="w")
else:
    outfile = sys.stdout

lastIdentifier = ""
while True:
    qs = (
        ezidapp.models.identifier.StoreIdentifier.objects.filter(
            identifier__gt=lastIdentifier
        )
        .order_by("identifier")
        .select_related("owner", "ownergroup", "datacenter", "profile")
    )
    qs = list(qs[:1000])
    if len(qs) == 0:
        break
    for si in qs:
        if options.excludeReserved and si.isReserved:
            continue
        d = si.toLegacy()
        if not options.rawOutput:
            ezidapp.models.model_util.convertLegacyToExternal(d)
        outfile.write(util.toExchange(d, si.identifier))
        outfile.write("\n")
    lastIdentifier = qs[-1].identifier

outfile.close()
