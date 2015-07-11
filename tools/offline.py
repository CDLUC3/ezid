# This file is execfile'd by offline scripts before importing any EZID
# modules, to set up the Python path and perform other initializations
# needed to prevent conflicts with the running server.  It can and
# should also be used when importing EZID modules interactively, as
# in:
#
# % python -i offline.py
# >>> import ezid
# >>> ...
#
# Greg Janee <gjanee@ucop.edu>
# July 2015

import os
import sys

if "DJANGO_SETTINGS_MODULE" not in os.environ:
  sys.stderr.write(
    "The DJANGO_SETTINGS_MODULE environment variable is not set.\n")
  sys.exit(1)

# Set the Python path.

try:
  import settings
except ImportError:
  sys.path.append(os.path.split(os.path.split(
    os.path.abspath(__file__))[0])[0])
  import settings

# Bootstrapping: reference a(ny) Django setting to trigger the loading
# of said settings, which causes the Python path to be further
# modified, supporting subsequent imports.

import django.conf
django.conf.settings.PROJECT_ROOT

# Configure the logging so that errors don't get added to the server's
# log file.  Also, disable daemon threads.

django.conf.settings.LOGGING_CONFIG_FILE = "logging.offline.conf"
django.conf.settings.DAEMON_THREADS_ENABLED = False
