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
# Standard coding practice: to support dynamic configuration
# reloading, if a module caches any configuration parameters in module
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

_loaders = []

def addLoader (loader):
  """
  Adds a reload listener.
  """
  _loaders.append(loader)

_config = None
_level = None

def load ():
  """
  (Re)loads the configuration file.
  """
  global _config, _level
  config = ConfigParser.ConfigParser({
    "SITE_ROOT": django.conf.settings.SITE_ROOT,
    "PROJECT_ROOT": django.conf.settings.PROJECT_ROOT })
  f = open(django.conf.settings.EZID_CONFIG_FILE)
  config.readfp(f)
  f.close()
  _config = config
  _level = "{%s}" % django.conf.settings.DEPLOYMENT_LEVEL
  for l in _loaders: l()

load()

def config (option):
  """
  Returns the value of a configuration option.  The option name should
  be specified in section.option syntax, e.g., "datacite.username".
  """
  s, o = option.split(".")
  if _config.has_option(s, _level+o):
    return _config.get(s, _level+o)
  else:
    return _config.get(s, o)
