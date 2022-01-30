#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Reads from standard input and writes to standard output, converting a raw dump to a
normal dump.

Usage:

   convert-dump [-m IDMAP] [-z]

If the -z option is specified, both the input and output are gzip-compressed. The -m
option uses IDMAP instead of the instance database for conversion of agent identifiers;
the specified IDMAP mapping file must be one produced by the 'idmap' script.

This script requires several EZID modules. The PYTHONPATH environment variable must
include the .../SITE_ROOT/PROJECT_ROOT directory; if it doesn't, we attempt to
dynamically locate it and add it. The DJANGO_SETTINGS_MODULE environment variable must
be set.
"""

import gzip
import optparse
import sys

import ezidapp.models.model_util
from impl import util

p = optparse.OptionParser(usage="%prog [-m IDMAP] [-z]")
p.add_option(
    "-m",
    action="store",
    type="string",
    dest="idmap",
    default=None,
    help="map agent identifiers to local names using IDMAP",
)
p.add_option(
    "-z", action="store_true", dest="gzip", default=False, help="gzip input/output"
)
options, args = p.parse_args()
if len(args) != 0:
    p.error("wrong number of arguments")

if options.idmap:
    agentMap = {"anonymous": "anonymous"}
    f = open(options.idmap)
    for l in f:
        id, name, agentType = l.split()
        agentMap[id] = name
    f.close()
else:
    agentMap = None

if options.gzip:
    infile = gzip.GzipFile(fileobj=sys.stdin, mode="r")
    outfile = gzip.GzipFile(fileobj=sys.stdout, mode="w")
else:
    infile = sys.stdin
    outfile = sys.stdout

for l in infile:
    id, record = util.fromExchange(l, identifierEmbedded=True)
    if agentMap is not None:
        record["_o"] = agentMap.get(record["_o"], record["_o"])
        record["_g"] = agentMap.get(record["_g"], record["_g"])
    ezidapp.models.model_util.convertLegacyToExternal(
        record, convertAgents=(agentMap is None)
    )
    outfile.write(util.toExchange(record, id))
    outfile.write("\n")

outfile.close()
