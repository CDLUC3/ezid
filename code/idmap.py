# =============================================================================
#
# EZID :: idmap.py
#
# Mapping between agent identifiers and user and group local names.
# Notice the handling of anonymous users.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2011, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import threading

import config
import ezidadmin

_lock = threading.Lock()
_ldapEnabled = None
_idMap = None
_groupMap = None
_userMap = None

def _loadConfig ():
  global _ldapEnabled, _idMap, _groupMap, _userMap
  _ldapEnabled = (config.get("ldap.enabled").lower() == "true")
  _lock.acquire()
  try:
    _idMap = None
    _groupMap = None
    _userMap = None
  finally:
    _lock.release()

_loadConfig()
config.registerReloadListener(_loadConfig)

def _loadLdapIds ():
  global _idMap, _groupMap, _userMap
  idMap = {}
  groupMap = {}
  userMap = {}
  groups = ezidadmin.getGroups()
  assert type(groups) is list, "ezidadmin.getGroups failed: " + groups
  for g in groups:
    idMap[g["arkId"]] = (g["gid"], "group")
    groupMap[g["gid"]] = g["arkId"]
  users = ezidadmin.getUsers()
  assert type(users) is list, "ezidadmin.getUsers failed: " + users
  for u in users:
    idMap[u["arkId"]] = (u["uid"], "user")
    userMap[u["uid"]] = u["arkId"]
  _idMap = idMap
  _groupMap = groupMap
  _userMap = userMap

def _loadLocalIds ():
  global _idMap, _groupMap, _userMap
  idMap = {}
  groupMap = {}
  userMap = {}
  for g in config.get("groups.keys").split(","):
    id = config.get("group_%s.id" % g)
    assert id not in idMap, "duplicate agent identifier: " + id
    idMap[id] = (g, "group")
    groupMap[g] = id
  for u in config.get("users.keys").split(","):
    id = config.get("user_%s.id" % u)
    assert id not in idMap, "duplicate agent identifier: " + id
    idMap[id] = (u, "user")
    userMap[u] = id
  _idMap = idMap
  _groupMap = groupMap
  _userMap = userMap

def _loadIds ():
  if _ldapEnabled:
    _loadLdapIds()
  else:
    _loadLocalIds()

def getAgent (id):
  """
  Given an agent identifier (e.g., "ark:/99166/foo"), returns a tuple
  (localName, agentType).  The agent type is either "user" or "group".
  Throws an exception on error.
  """
  if id == "anonymous": return ("anonymous", "user")
  _lock.acquire()
  try:
    if _idMap is None: _loadIds()
    assert id in _idMap, "unknown agent identifier: " + id
    return _idMap[id]
  finally:
    _lock.release()

def getGroupId (group):
  """
  Returns an agent identifier (e.g., "ark:/99166/foo") given a group
  local name (e.g., "dryad").  Throws an exception on error.
  """
  if group == "anonymous": return "anonymous"
  _lock.acquire()
  try:
    if _groupMap is None: _loadIds()
    # Module download relies on the formatting of the following error
    # message.
    assert group in _groupMap, "unknown group: " + group
    return _groupMap[group]
  finally:
    _lock.release()

def getUserId (user):
  """
  Returns an agent identifier (e.g., "ark:/99166/foo") given a user
  local name (e.g., "ryan").  Throws an exception on error.
  """
  if user == "anonymous": return "anonymous"
  _lock.acquire()
  try:
    if _userMap is None: _loadIds()
    # Modules ezid and download rely on the formatting of the
    # following error message.
    assert user in _userMap, "unknown user: " + user
    return _userMap[user]
  finally:
    _lock.release()

def addGroup (group, id):
  """
  Adds a mapping between a group local name (e.g., "dryad") and an
  agent identifier (e.g., "ark:/99166/foo").  Throws an exception on
  error.
  """
  _lock.acquire()
  try:
    if _groupMap is None: _loadIds()
    if group in _groupMap:
      assert _groupMap[group] == id,\
        "inconsistent agent identifier for group '%s'" % group
    else:
      assert id not in _idMap, "duplicate agent identifier: " + id
      _idMap[id] = (group, "group")
      _groupMap[group] = id
  finally:
    _lock.release()

def addUser (user, id):
  """
  Adds a mapping between a user local name (e.g., "ryan") and an agent
  identifier (e.g., "ark:/99166/foo").  Throws an exception on error.
  """
  _lock.acquire()
  try:
    if _userMap is None: _loadIds()
    if user in _userMap:
      assert _userMap[user] == id,\
        "inconsistent agent identifier for user '%s'" % user
    else:
      assert id not in _idMap, "duplicate agent identifier: " + id
      _idMap[id] = (user, "user")
      _userMap[user] = id
  finally:
    _lock.release()
