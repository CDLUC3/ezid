#! /usr/bin/env python

# Dumps a noid "egg" binder database to standard output.
#
# Usage: dump-binder [-rz] egg.bdb
#
# Options:
#   -r raw dump
#   -z gzip the output
#
# Note: identifiers are NOT written in lexicographic order.
#
# This script requires several EZID modules.  The PYTHONPATH
# environment variable must include the .../SITE_ROOT/PROJECT_ROOT
# directory; if it doesn't, we attempt to dynamically locate it and
# add it.  The DJANGO_SETTINGS_MODULE environment variable must be
# set.
#
# Greg Janee <gjanee@ucop.edu>
# December 2011

import gzip
import optparse
import sys

import bsddb3.db

import ezidapp.models.model_util
from impl import noid_egg
from impl import util

p = optparse.OptionParser(usage="%prog [-rz] egg.bdb")
p.add_option(
    "-r", action="store_true", dest="rawOutput", default=False, help="raw dump"
)
p.add_option(
    "-z", action="store_true", dest="gzipOutput", default=False, help="gzip output"
)
options, args = p.parse_args()
if len(args) != 1:
    p.error("wrong number of arguments")

if options.gzipOutput:
    outfile = gzip.GzipFile(fileobj=sys.stdout, mode="w")
else:
    outfile = sys.stdout


def outputRecord(identifier, record):
    try:
        for k in ["_o", "_g", "_c", "_u", "_t", "_p"]:
            assert k in record, "missing field: " + k
        if not options.rawOutput:
            ezidapp.models.model_util.convertLegacyToExternal(record)
        outfile.write(util.toExchange(record, identifier))
        outfile.write("\n")
    except Exception as e:
        sys.stderr.write(
            "\nInvalid record: {}\n{}\nRecord: {}\n".format(
                identifier, util.formatException(e), repr(record)
            )
        )


db = bsddb3.db.DB()
db.open(args[0], flags=bsddb3.db.DB_RDONLY)
cursor = db.cursor()
entry = cursor.first()
lastId = None
while entry is not None:
    k, value = entry
    if "|" in k:
        id, label = k.split("|", 1)
        id = noid_egg.decodeRaw(id)
        label = noid_egg.decodeRaw(label)
        value = value.decode("UTF-8")
        if (
            util.validateIdentifier(id) == id
            and not label.startswith("__")
            and not label.startswith("_.e")
            and not label.startswith("_,e")
        ):
            # The fundamental assumption of this loop is that bindings
            # (binding = identifier + "|" + label) are stored in
            # lexicographic order.  But that doesn't imply that identifiers
            # themselves are returned in lexicographic order.
            if id != lastId:
                if lastId is not None:
                    # noinspection PyUnboundLocalVariable
                    outputRecord(lastId, record)
                record = {}
            # noinspection PyUnboundLocalVariable
            record[label] = value
            lastId = id
    entry = next(cursor)
if lastId is not None:
    outputRecord(lastId, record)
db.close()

outfile.close()
