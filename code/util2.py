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
import ezidapp.models

_ezidUrl = None
_arkTestPrefix = None
_doiTestPrefix = None
_defaultArkProfile = None
_defaultDoiProfile = None
_defaultUuidProfile = None

def _loadConfig ():
  global _ezidUrl, _arkTestPrefix, _doiTestPrefix, _defaultArkProfile
  global _defaultDoiProfile, _defaultUuidProfile
  _ezidUrl = config.get("DEFAULT.ezid_base_url")
  _arkTestPrefix = config.get("shoulders.ark_test")
  _doiTestPrefix = config.get("shoulders.doi_test")
  _defaultArkProfile = config.get("DEFAULT.default_ark_profile")
  _defaultDoiProfile = config.get("DEFAULT.default_doi_profile")
  _defaultUuidProfile = config.get("DEFAULT.default_uuid_profile")

_loadConfig()
config.registerReloadListener(_loadConfig)

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

def isTestArk (identifier):
  """
  Returns True if the supplied unqualified ARK (e.g., "12345/foo") is
  a test identifier.
  """
  return identifier.startswith(_arkTestPrefix[5:])

def isTestDoi (identifier):
  """
  Returns True if the supplied unqualified DOI (e.g., "10.1234/FOO")
  is a test identifier.
  """
  return identifier.startswith(_doiTestPrefix[4:])

def defaultProfile (identifier):
  """
  Returns the label of the default metadata profile (e.g., "erc") for
  a given qualified identifier.
  """
  if identifier.startswith("ark:/"):
    return _defaultArkProfile
  elif identifier.startswith("doi:"):
    return _defaultDoiProfile
  elif identifier.startswith("uuid:"):
    return _defaultUuidProfile
  else:
    assert False, "unhandled case"

_labelMapping = {
  "_o": "_owner",
  "_g": "_ownergroup",
  "_c": "_created",
  "_u": "_updated",
  "_t": "_target",
  "_p": "_profile",
  "_is": "_status",
  "_x": "_export",
  "_d": "_datacenter",
  "_cr": "_crossref"
}

def convertLegacyToExternal (d, convertAgents=True):
  """
  Converts a legacy metadata dictionary from internal form (i.e., as
  stored in the Noid "egg" binder) to external form (i.e., as returned
  to clients).  The dictionary is modified in place.  N.B.: if the
  dictionary is for a non-ARK identifier, this function does *not* add
  the _shadowedby element.
  """
  if "_is" not in d: d["_is"] = "public"
  if "_x" not in d: d["_x"] = "yes"
  if convertAgents:
    u = ezidapp.models.getUserByPid(d["_o"])
    if u != None: d["_o"] = u.username
    g = ezidapp.models.getGroupByPid(d["_g"])
    if g != None: d["_g"] = g.groupname
  if d["_is"] != "public":
    d["_t"] = d["_t1"]
    del d["_t1"]
  for k in d.keys():
    if k in _labelMapping:
      d[_labelMapping[k]] = d[k]
      del d[k]
