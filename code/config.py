# =============================================================================
#
# EZID :: config.py
#
# Interface to the configuration file.
#
# In an extension to Python's configuration file format, we allow an
# option to be prefixed with a deployment level in braces, e.g.,
#
#   {production}the_answer: 42
#
# If a deployment-level-specific value for an option corresponding to
# the current deployment level exists, that value is used; otherwise,
# the value for the option with no deployment level is used.
#
# Also, if a "shadow" configuration file is present, it too is loaded
# and takes precedence over the nominal configuration file.  The
# intention is that passwords and other sensitive information can be
# stored in the shadow configuration file, which is not included in
# the EZID source code repository.
#
# Standard coding practice: to support dynamic configuration
# reloading, if a module caches any configuration options in module
# variables, upon being initially loaded it should call
# config.addLoader to add a reload function.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2010, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.conf
import os.path
import subprocess
import time

import config_loader
import ezidapp.models.search_identifier

_loaders = []

def addLoader (loader):
  """
  Adds a reload listener.
  """
  _loaders.append(loader)

_config = None
_version = None
_startupVersion = None

def _getVersion1 (r):
  try:
    p = subprocess.Popen(["hg", "identify", "-inb", "-R", r],
      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    o = p.communicate()[0]
    if p.returncode == 0:
      return o.strip()
    else:
      return "unknown"
  except:
    return "unknown"

def _getVersion ():
  return (_getVersion1(django.conf.settings.PROJECT_ROOT),
    _getVersion1(os.path.join(django.conf.settings.PROJECT_ROOT, "templates",
      "info")))

def _load ():
  global _config, _version
  _config = config_loader.Config(django.conf.settings.SITE_ROOT,
    django.conf.settings.PROJECT_ROOT, django.conf.settings.EZID_CONFIG_FILE,
    django.conf.settings.EZID_SHADOW_CONFIG_FILE,
    django.conf.settings.DEPLOYMENT_LEVEL)
  _version = (int(time.time()),) + _getVersion()

def reload ():
  """
  Reloads the configuration file.
  """
  _load()
  for l in _loaders: l()
  ezidapp.models.search_identifier.clearProfileCache()

_load()
_startupVersion = _version

def config (option):
  """
  Returns the value of a configuration option.  The option name should
  be specified in section.option syntax, e.g., "datacite.username".
  """
  return _config.getOption(option)

def getVersionInfo ():
  """
  Returns two tuples, each of the form (timestamp, ezidVersion,
  infoVersion).  The first tuple reflects the state of EZID's
  Mercurial repositories at the time of server startup, the second at
  the time of the last configuration reload.  Within each tuple, the
  first element is the startup or reload time as a Unix timestamp, the
  second is the EZID repository's version, and the third is the info
  repository's version.
  """
  return (_startupVersion, _version)

# Start daemon threads by importing their modules.
if django.conf.settings.DAEMON_THREADS_ENABLED:
  import backproc
  import crossref
  import datacite_async
  import download
  import newsfeed
  import status
