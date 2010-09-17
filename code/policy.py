# =============================================================================
#
# EZID :: policy.py
#
# Authorization policy.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2010, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import threading

import config

_lock = threading.Lock()
_prefixes = None
_groups = None

def _loadConfig ():
  global _prefixes, _groups
  _lock.acquire()
  _prefixes = dict([k, config.config("prefix_%s.prefix" % k)]\
    for k in config.config("prefixes.keys").split(","))
  _groups = {}
  _lock.release()

_loadConfig()
config.addLoader(_loadConfig)

def _loadPrefixes (group):
  ### STUB ###
  # any errors should be raised as exceptions
  if group[0] == "admin":
    return [_prefixes[k] for k in config.config("prefixes.keys").split(",")\
      if k != "TESTARK" and k != "TESTDOI"]
  elif group[0] == "anonymous":
    return []
  elif group[0] == "cdl":
    return [_prefixes["cdlark"], _prefixes["cdldoi"]]
  elif group[0] == "dryad":
    return [_prefixes["dryad"], _prefixes["cdlark"]]
  elif group[0] == "merritt":
    return [_prefixes["merritt"], _prefixes["cdlcollection"],
      _prefixes["cdlark"], _prefixes["cdldoi"]]
  else:
    assert False, "group not found"
  ### STUB ###

def _getPrefixes (group):
  _lock.acquire()
  try:
    if group in _groups:
      return _groups[group]
    else:
      _groups[group] = _loadPrefixes(group)
      return _groups[group]
  finally:
    _lock.release()

def getPrefixes (user, group):
  """
  Returns a list of the prefixes available to a user not including the
  test prefixes.  'user' and 'group' should each be authenticated
  (local name, persistent identifier) pairs, e.g., ("dryad",
  "ark:/13030/foo").  Throws an exception on error.
  """
  return _getPrefixes(group)[:]

def authorizeCreate (user, group, prefix):
  """
  Returns true if a request to mint or create an identifier is
  authorized.  'user' and 'group' should each be authenticated (local
  name, persistent identifier) pairs, e.g., ("dryad",
  "ark:/13030/foo").  'prefix' may be a complete identifier or just a
  prefix of one; in either case it must be qualified, e.g.,
  "doi:10.5060/".  Throws an exception on error.
  """
  return prefix.startswith(_prefixes["TESTARK"]) or\
    prefix.startswith(_prefixes["TESTDOI"]) or\
    len(filter(lambda p: prefix.startswith(p), _getPrefixes(group))) > 0

def authorizeUpdate (rUser, rGroup, identifier, iUser, iGroup):
  """
  Returns true if a request to update an existing identifier is
  authorized.  'rUser' and 'rGroup' identify the requester and should
  each be authenticated (local name, persistent identifier) pairs,
  e.g., ("dryad", "ark:/13030/foo"); 'iUser' and 'iGroup' should be
  similar quantities that identify the identifier's owner.
  'identifier' is the identifier in question; it must be qualified, as
  in "doi:10.5060/foo".  Throws an exception on error.
  """
  return identifier.startswith(_prefixes["TESTARK"]) or\
    identifier.startswith(_prefixes["TESTDOI"]) or rUser == iUser or\
    rUser[0] == "admin"
