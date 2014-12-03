# =============================================================================
#
# EZID :: oai.py
#
# Support for OAI-PMH 2.0
# <http://www.openarchives.org/OAI/openarchivesprotocol.html>.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2014, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import threading
import urllib

import config
import mapping
import shoulder

_lock = threading.Lock()
_testShoulders = None
_ezidUrl = None

def _loadConfig ():
  global _testShoulders, _ezidUrl
  _lock.acquire()
  _testShoulders = None
  _lock.release()
  _ezidUrl = config.config("DEFAULT.ezid_base_url")

_loadConfig()
config.addLoader(_loadConfig)

def _getTestShoulders ():
  global _testShoulders
  _lock.acquire()
  try:
    if _testShoulders is None:
      _testShoulders = []
      s = shoulder.getArkTestShoulder()
      if s is not None: _testShoulders.append(s.key)
      s = shoulder.getDoiTestShoulder()
      if s is not None: _testShoulders.append(s.key)
    return _testShoulders
  finally:
    _lock.release()

def _defaultTarget (identifier):
  return "%s/id/%s" % (_ezidUrl, urllib.quote(identifier, ":/"))

def isVisible (identifier, metadata):
  """
  Returns true if 'identifier' is (should be) visible in the OAI-PMH
  feed.  'identifier' should be a qualified, normalized identifier,
  e.g., "doi:10.5060/FOO".  'metadata' should be the identifier's
  metadata as a dictionary.
  """
  if any(identifier.startswith(s) for s in _getTestShoulders()): return False
  # Well, isn't this subtle and ugly: this function gets called by the
  # 'store' module, in which case the metadata dictionary contains
  # noid commands to *change* metadata values, not the final stored
  # values.  Ergo, we have to check for empty values.
  status = metadata.get("_is", "public")
  if status == "": status = "public"
  if status != "public": return False
  export = metadata.get("_x", "yes")
  if export == "": export = "yes"
  if export != "yes": return False
  if metadata.get("_st", metadata["_t"]) == _defaultTarget(identifier):
    return False
  m = mapping.getDisplayMetadata(metadata)
  if m[0] is None or m[1] is None or m[3] is None: return False
  return True
