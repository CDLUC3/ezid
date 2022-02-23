#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""The 'dump-store', 'dump-binder', 'select', and 'project' scripts form a dump file
query system.

The general usage is:

   dump-* | select constraint... | project fields...

This script reads a dump file (normal or raw) from standard input and writes selected
fields from those records to standard output.

Usage: project [options] fields...

Options:
  -a            output all fields
  -d            decode labels and values
  -l            output labels
  -m IDMAP      convert agent identifiers to local names using IDMAP
  -o            one line per identifier: convert newlines to spaces
  -s SEPARATOR  field separator (defaults to space)
  -S SEPARATOR  label/value separator (defaults to =)
  -t            format timestamps
  -z            gunzip the input

The '_id' pseudo-field can be used to output the identifier itself.
If the -a option is given, any fields specified on the command line are ignored and
neither the order nor the presence of fields will be consistent from identifier to
identifier.

If values are decoded, they are re-UTF-8-encoded when output. Note that identifiers
themselves are never encoded.

The -m option is useful when reading records in which agent identifiers have *not* been
converted; the specified IDMAP mapping file must be one produced by the 'idmap' script.

This script requires an EZID module. The PYTHONPATH environment variable must include
the .../SITE_ROOT/PROJECT_ROOT/impl directory; if it doesn't, we attempt to dynamically
locate it and add it.
"""

import gzip
import optparse
import sys
import time

import impl.util

p = optparse.OptionParser(usage="%prog [options] fields...")
p.add_option(
    "-a", action="store_true", dest="allFields", default=False, help="output all fields"
)
p.add_option(
    "-d",
    action="store_false",
    dest="hexEncode",
    default=True,
    help="decode labels and values",
)
p.add_option(
    "-l", action="store_true", dest="outputLabels", default=False, help="output labels"
)
p.add_option(
    "-m",
    action="store",
    type="string",
    dest="idmap",
    default=None,
    help="map agent identifiers to local names using IDMAP",
)
p.add_option(
    "-o",
    action="store_true",
    dest="oneLine",
    default=False,
    help="one line per identifier: convert newlines to spaces",
)
p.add_option(
    "-s",
    action="store",
    type="string",
    dest="separator",
    default=" ",
    help="field separator (defaults to space)",
)
p.add_option(
    "-S",
    action="store",
    type="string",
    dest="labelValueSeparator",
    default="=",
    help="label/value separator (defaults to =)",
    metavar="SEPARATOR",
)
p.add_option(
    "-t",
    action="store_true",
    dest="formatTimestamps",
    default=False,
    help="format timestamps",
)
p.add_option(
    "-z",
    action="store_true",
    dest="gunzipInput",
    default=False,
    help="gunzip the input",
)
options, fields = p.parse_args()

if options.idmap:
    f = open(options.idmap)
    idmap = {}
    for l in f:
        id, name, agentType = l.split()
        idmap[id] = name
    f.close()

if options.gunzipInput:
    infile = gzip.GzipFile(fileobj=sys.stdin, mode="r")
else:
    infile = sys.stdin

for l in infile:
    id, r = impl.util.fromExchange(l, True)
    s = ""
    if options.allFields:
        fields = list(r.keys())
        fields.insert(0, "_id")
    for f in fields:
        sys.stdout.write(s)
        if options.outputLabels:
            if options.hexEncode:
                sys.stdout.write(impl.util.encode4(f))
            else:
                sys.stdout.write(f)
            sys.stdout.write(options.labelValueSeparator)
        if f == "_id":
            v = id
        elif f in r:
            if f in ["_c", "_created", "_u", "_updated"] and options.formatTimestamps:
                v = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(int(r[f])))
            elif f in ["_o", "_owner", "_g", "_ownergroup"] and options.idmap:
                # noinspection PyUnboundLocalVariable
                v = idmap.get(r[f], r[f])
            else:
                v = r[f]
        else:
            v = ""
        if options.hexEncode:
            if f != "_id":
                v = impl.util.encode3(v)
            sys.stdout.write(v)
        else:
            if options.oneLine:
                v = v.replace("\n", " ").replace("\r", " ")
            sys.stdout.buffer.write(v.encode("UTF-8"))
        s = options.separator
    sys.stdout.write("\n")
