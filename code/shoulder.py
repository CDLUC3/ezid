# =============================================================================
#
# EZID :: shoulder.py
#
# Identifier shoulders.
#
# Note that the functions in this module are designed to hide errors
# from the caller by always returning successfully (but errors are
# still logged).
#
# Shoulders are loaded primarily from a URL (and if that is
# successful, the shoulders are cached locally) and secondarily from a
# previously-written cache file.  If neither of those attempts is
# successful, an empty list of shoulders is created.
#
# This module adds two boolean attributes to returned
# shoulder_parser.Entry objects: is_test_shoulder and
# is_agent_shoulder.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2013, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import base64
import os.path
import threading
import urllib2

import config
import log
import shoulder_parser

_lock = threading.Lock()
_primaryUrl = None
_username = None
_password = None
_cacheFile = None
_arkTestShoulderKey = None
_doiTestShoulderKey = None
_agentShoulderKey = None
_shoulders = None
_arkTestShoulder = None
_doiTestShoulder = None
_agentShoulder = None

def _loadConfig ():
  global _primaryUrl, _username, _password, _cacheFile, _arkTestShoulderKey
  global _doiTestShoulderKey, _agentShoulderKey, _shoulders, _arkTestShoulder
  global _doiTestShoulder, _agentShoulder
  _lock.acquire()
  try:
    _primaryUrl = config.config("shoulders.primary_url")
    _username = config.config("shoulders.username")
    if _username != "":
      _password = config.config("shoulders.password")
    else:
      _username = None
      _password = None
    _cacheFile = config.config("shoulders.cache_file")
    _arkTestShoulderKey = config.config("shoulders.ark_test")
    _doiTestShoulderKey = config.config("shoulders.doi_test")
    _agentShoulderKey = config.config("shoulders.agent")
    _shoulders = None
    _arkTestShoulder = None
    _doiTestShoulder = None
    _agentShoulder = None
  finally:
    _lock.release()

_loadConfig()
config.addLoader(_loadConfig)

def _load1 (url):
  f = None
  try:
    r = urllib2.Request(url)
    if _username != None:
      r.add_header("Authorization", "Basic " +\
        base64.b64encode("%s:%s" % (_username, _password)))
    f = urllib2.urlopen(r)
    content = f.read()
  finally:
    if f: f.close()
  entries, errors, warnings = shoulder_parser.parse(content)
  assert len(errors) == 0, "validation error(s): " +\
    ", ".join("(line %d) %s" % e for e in errors)
  shoulders = dict((e.key, e) for e in entries if e.type == "shoulder" and\
    e.manager == "ezid" and e.active)
  for shoulder in shoulders.itervalues():
    shoulder.is_test_shoulder = False
    shoulder.is_agent_shoulder = False
  assert _arkTestShoulderKey in shoulders,\
    "no definition for ARK test shoulder"
  arkTestShoulder = shoulders[_arkTestShoulderKey]
  arkTestShoulder.is_test_shoulder = True
  assert _doiTestShoulderKey in shoulders,\
    "no definition for DOI test shoulder"
  doiTestShoulder = shoulders[_doiTestShoulderKey]
  doiTestShoulder.is_test_shoulder = True
  assert _agentShoulderKey in shoulders, "no definition for agent shoulder"
  agentShoulder = shoulders[_agentShoulderKey]
  agentShoulder.is_agent_shoulder = True
  return (content, shoulders, arkTestShoulder, doiTestShoulder, agentShoulder)

def _wrapException (context, exception):
  m = str(exception)
  if len(m) > 0: m = ": " + m
  return Exception("%s: %s%s" % (context, type(exception).__name__, m))

def _load ():
  # Assumption: lock has been acquired and _shoulders, etc., are None.
  global _shoulders, _arkTestShoulder, _doiTestShoulder, _agentShoulder
  try:
    content, _shoulders, _arkTestShoulder, _doiTestShoulder,\
      _agentShoulder = _load1(_primaryUrl)
  except Exception, e:
    log.otherError("shoulder._load",
      _wrapException("error loading shoulders from primary source", e))
    try:
      content, _shoulders, _arkTestShoulder, _doiTestShoulder,\
        _agentShoulder = _load1("file://" + os.path.abspath(_cacheFile))
    except Exception, e:
      log.otherError("shoulder._load",
        _wrapException("error loading shoulders from cache file", e))
  else:
    try:
      f = open(_cacheFile, "w")
      f.write(content)
      f.close()
    except Exception, e:
      log.otherError("shoulder._load",
        _wrapException("error caching shoulders", e))

def _loadAndLock (f):
  # Decorator.
  def wrapped (*args, **kwargs):
    _lock.acquire()
    try:
      if _shoulders is None: _load()
      return f(*args, **kwargs)
    finally:
      _lock.release()
  return wrapped

@_loadAndLock
def getAll ():
  """
  Returns all shoulders as a list of shoulder_parser.Entry objects.
  """
  return _shoulders.values()

@_loadAndLock
def getAllMatches (identifier):
  """
  Returns a list of all shoulders that match 'identifier', i.e., that
  are a prefix of 'identifier'.
  """
  return [s for s in _shoulders.itervalues() if identifier.startswith(s.key)]

def getLongestMatch (identifier):
  """
  Returns the longest shoulder that matches 'identifier', i.e., that
  is a prefix of 'identifier'.
  """
  lm = None
  for s in getAllMatches(identifier):
    if lm is None or len(s.key) > len(lm.key): lm = s
  return lm

@_loadAndLock
def getExactMatch (key):
  """
  Returns the shoulder_parser.Entry object for shoulder 'key', or
  None.
  """
  return _shoulders.get(key, None)

@_loadAndLock
def getArkTestShoulder ():
  """
  Returns the ARK test shoulder as a shoulder_parser.Entry object (or
  None in the erroneous and exceptional case that the shoulder isn't
  defined).
  """
  return _arkTestShoulder

@_loadAndLock
def getDoiTestShoulder ():
  """
  Returns the DOI test shoulder as a shoulder_parser.Entry object (or
  None in the erroneous and exceptional case that the shoulder isn't
  defined).
  """
  return _doiTestShoulder

@_loadAndLock
def getAgentShoulder ():
  """
  Returns the agent shoulder as a shoulder_parser.Entry object (or
  None in the erroneous and exceptional case that the shoulder isn't
  defined).
  """
  return _agentShoulder
