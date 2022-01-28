#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Deletes all session cookies for a given user

Usage:

Usage: delete-sessions username

This script requires several EZID modules.  The PYTHONPATH environment variable must
include the .../SITE_ROOT/PROJECT_ROOT directory; if it doesn't, we attempt to
dynamically locate it and add it.  The DJANGO_SETTINGS_MODULE environment variable must
be set.
"""

import sys

# import django_util
import impl.django_util

if len(sys.argv) != 2:
    sys.stderr.write("Usage: delete-sessions username\n")
    sys.exit(1)

n = impl.django_util.deleteSessions(sys.argv[1])
print(f"{n:d} session{'s' if n != 1 else ''} deleted")
