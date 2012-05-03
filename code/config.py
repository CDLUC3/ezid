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

import ConfigParser
import django.conf
import os.path
import subprocess
import time

_loaders = []

def addLoader (loader):
  """
  Adds a reload listener.
  """
  _loaders.append(loader)

_config = None
_shadowConfig = None
_level = None
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

def load ():
  """
  (Re)loads the configuration file.
  """
  global _config, _shadowConfig, _level, _version
  config = ConfigParser.ConfigParser({
    "SITE_ROOT": django.conf.settings.SITE_ROOT,
    "PROJECT_ROOT": django.conf.settings.PROJECT_ROOT })
  f = open(django.conf.settings.EZID_CONFIG_FILE)
  config.readfp(f)
  f.close()
  _config = config
  config = ConfigParser.ConfigParser()
  if os.path.exists(django.conf.settings.EZID_SHADOW_CONFIG_FILE):
    f = open(django.conf.settings.EZID_SHADOW_CONFIG_FILE)
    config.readfp(f)
    f.close()
  _shadowConfig = config
  _level = "{%s}" % django.conf.settings.DEPLOYMENT_LEVEL
  _version = (int(time.time()),) + _getVersion()
  for l in _loaders: l()

load()
_startupVersion = _version

def config (option):
  """
  Returns the value of a configuration option.  The option name should
  be specified in section.option syntax, e.g., "datacite.username".
  """
  s, o = option.split(".")
  if _shadowConfig.has_option(s, _level+o):
    return _shadowConfig.get(s, _level+o)
  elif _config.has_option(s, _level+o):
    return _config.get(s, _level+o)
  elif _shadowConfig.has_option(s, o):
    return _shadowConfig.get(s, o)
  else:
    return _config.get(s, o)

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
