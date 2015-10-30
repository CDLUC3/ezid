# =============================================================================
#
# EZID :: util2.py
#
# Utility functions that require that EZID's configuration be loaded.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import urllib

import config

_ezidUrl = None
_arkTestPrefix = None
_doiTestPrefix = None
_defaultArkProfile = None
_defaultDoiProfile = None
_defaultUrnUuidProfile = None

def _loadConfig ():
  global _ezidUrl, _arkTestPrefix, _doiTestPrefix, _defaultArkProfile
  global _defaultDoiProfile, _defaultUrnUuidProfile
  _ezidUrl = config.config("DEFAULT.ezid_base_url")
  _arkTestPrefix = config.config("shoulders.ark_test")
  _doiTestPrefix = config.config("shoulders.doi_test")
  _defaultArkProfile = config.config("DEFAULT.default_ark_profile")
  _defaultDoiProfile = config.config("DEFAULT.default_doi_profile")
  _defaultUrnUuidProfile = config.config("DEFAULT.default_urn_uuid_profile")

_loadConfig()
config.addLoader(_loadConfig)

def defaultTargetUrl (identifier):
  """
  Returns the default target URL for an identifier.  The identifier
  is assumed to be in normalized, qualified form.
  """
  return "%s/id/%s" % (_ezidUrl, urllib.quote(identifier, ":/"))

def tombstoneTargetUrl (identifier):
  """
  Returns the "tombstone" target URL for an identifier.  The
  identifier is assumed to be in normalized, qualified form.
  """
  return "%s/tombstone/id/%s" % (_ezidUrl, urllib.quote(identifier, ":/"))

def isTestIdentifier (identifier):
  """
  Returns True if the supplied qualified identifier is a test
  identifier.
  """
  return identifier.startswith(_arkTestPrefix) or\
    identifier.startswith(_doiTestPrefix)

def defaultProfile (identifier):
  """
  Returns the label of the default metadata profile (e.g., "erc") for
  a given qualified identifier.
  """
  if identifier.startswith("ark:/"):
    return _defaultArkProfile
  elif identifier.startswith("doi:"):
    return _defaultDoiProfile
  elif identifier.startswith("urn:uuid:"):
    return _defaultUrnUuidProfile
  else:
    assert False, "unhandled case"
