#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Decodes a hex-encoded file.

The file is overwritten.

This script requires an EZID module. The PYTHONPATH environment variable must include
the .../SITE_ROOT/PROJECT_ROOT/impl directory; if it doesn't, we attempt to dynamically
locate it and add it.
"""
import sys

from impl import util

if len(sys.argv) != 2:
    sys.stderr.write("Usage: decode-file file\n")
    sys.exit(1)

f = open(sys.argv[1], "r+")
s = f.read()
f.seek(0)
f.write(util.decode(s).encode("UTF-8"))
f.flush()
f.truncate()
f.close()
