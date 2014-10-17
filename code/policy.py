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

import ldap
import threading

import config
import log
import shoulder
import useradmin

_lock = threading.Lock()
_testShoulders = None
_groups = None
_coOwners = None
_ldapEnabled = None
_ldapServer = None
_userDnTemplate = None
_adminUsername = None
_adminPassword = None

def _loadConfig ():
  global _testShoulders, _groups, _coOwners, _ldapEnabled
  global _ldapServer, _userDnTemplate, _adminUsername, _adminPassword
  _lock.acquire()
  try:
    _testShoulders = None
    _groups = {}
    _coOwners = {}
    _ldapEnabled = (config.config("ldap.enabled").lower() == "true")
    _ldapServer = config.config("ldap.server")
    _userDnTemplate = config.config("ldap.user_dn_template")
    _adminUsername = config.config("ldap.admin_username")
    _adminPassword = config.config("ldap.admin_password")
  finally:
    _lock.release()

_loadConfig()
config.addLoader(_loadConfig)

def _lookupShoulders (group, shoulderText):
  if shoulderText == "NONE": return []
  l = []
  for s in shoulderText.split():
    try:
      entry = shoulder.getExactMatch(s)
      assert entry != None, "group '%s' has undefined shoulder: %s" %\
        (group[0], s)
      if entry not in l: l.append(entry)
    except AssertionError, e:
      log.otherError("policy._lookupShoulders", e)
  return l

def _loadShouldersLdap (group):
  l = None
  try:
    l = ldap.initialize(_ldapServer)
    l.bind_s(_userDnTemplate % _adminUsername, _adminPassword,
      ldap.AUTH_SIMPLE)
    r = l.search_s(group[2], ldap.SCOPE_BASE)
    assert len(r) == 1 and r[0][0].lower() == group[2].lower() and\
      "ezidGroup" in r[0][1]["objectClass"] and\
      len(r[0][1]["shoulderList"]) == 1,\
      "unexpected return from LDAP search command, DN='%s'" % group[2]
    # Although not documented anywhere, it appears that returned
    # values are UTF-8 encoded.
    return _lookupShoulders(group, r[0][1]["shoulderList"][0].decode("UTF-8"))
  finally:
    if l: l.unbind()

def _loadShouldersLocal (group):
  return _lookupShoulders(group,
    config.config("group_%s.shoulders" % group[0]))

def _loadShoulders (group):
  if group[0] == _adminUsername:
    return [s for s in shoulder.getAll() if not s.is_test_shoulder]
  elif group[0] == "anonymous":
    return []
  elif _ldapEnabled:
    return _loadShouldersLdap(group)
  else:
    return _loadShouldersLocal(group)

def _getShoulders (group):
  _lock.acquire()
  try:
    if group in _groups:
      return _groups[group]
    else:
      _groups[group] = _loadShoulders(group)
      return _groups[group]
  finally:
    _lock.release()

def getShoulders (user, group):
  """
  Returns a list of the shoulders available to a user not including
  the test shoulders.  'user' and 'group' should each be authenticated
  (local name, persistent identifier) tuples, e.g., ("dryad",
  "ark:/13030/foo").  Each shoulder is described by a
  shoulder_parser.Entry object.  Throws an exception on error.
  """
  return _getShoulders(group)[:]

def clearShoulderCache (group):
  """
  Clears the shoulder cache for a group.  'group' should be a simple
  group name, e.g., "dryad".
  """
  _lock.acquire()
  try:
    for g in _groups:
      if g[0] == group:
        del _groups[g]
        break
  finally:
    _lock.release()

def _getTestShoulders ():
  global _testShoulders
  _lock.acquire()
  try:
    if _testShoulders is None:
      _testShoulders = []
      s = shoulder.getArkTestShoulder()
      try:
        assert s is not None, "no ARK test shoulder"
      except AssertionError, e:
        log.otherError("policy._getTestShoulders", e)
      else:
        _testShoulders.append(s)
      s = shoulder.getDoiTestShoulder()
      try:
        assert s is not None, "no DOI test shoulder"
      except AssertionError, e:
        log.otherError("policy._getTestShoulders", e)
      else:
        _testShoulders.append(s)
    return _testShoulders
  finally:
    _lock.release()

def _loadCoOwnersLdap (user):
  l = None
  try:
    l = ldap.initialize(_ldapServer)
    l.bind_s(_userDnTemplate % _adminUsername, _adminPassword,
      ldap.AUTH_SIMPLE)
    dn = _userDnTemplate % ldap.dn.escape_dn_chars(user)
    r = l.search_s(dn, ldap.SCOPE_BASE, attrlist=["objectClass",
      "ezidCoOwners"])
    assert len(r) == 1 and r[0][0].lower() == dn.lower() and\
      "ezidUser" in r[0][1]["objectClass"],\
      "unexpected return from LDAP search command, DN='%s'" % dn
    if "ezidCoOwners" in r[0][1]:
      col = useradmin.validateCoOwnerList(l,
        r[0][1]["ezidCoOwners"][0].decode("UTF-8"))
      assert col is not None,\
        "no such EZID user in co-owner list, DN='%s'" % dn
      return col
    else:
      return []
  finally:
    if l: l.unbind()

def _loadCoOwnersLocal (user):
  return [o for o in config.config("user_%s.co_owners" % user).split(",")\
    if len(o) > 0]

def _loadCoOwners (user):
  if _ldapEnabled:
    return _loadCoOwnersLdap(user)
  else:
    return _loadCoOwnersLocal(user)

def _getCoOwners (user):
  if user == "anonymous": return []
  _lock.acquire()
  try:
    if user not in _coOwners: _coOwners[user] = _loadCoOwners(user)
    return _coOwners[user]
  finally:
    _lock.release()

def clearCoOwnerCache (user):
  """
  Clears the co-owner cache for a user.  'user' should be a simple
  username, e.g., "ryan".
  """
  _lock.acquire()
  try:
    if user in _coOwners: del _coOwners[user]
  finally:
    _lock.release()

def authorizeView (user, group, identifier, metadata):
  """
  Returns true if a request to view identifier metadata is authorized.
  'user' and 'group' should each be authenticated (local name,
  persistent identifier) tuples, e.g., ("dryad", "ark:/13030/foo").
  'identifier' is the identifier in question; it must be qualified, as
  in "doi:10.5060/foo".  'metadata' is the identifier's metadata as a
  dictionary of (name, value) pairs.
  """
  return "_ezid_role" not in metadata or user[0] == _adminUsername

def authorizeCreate (user, group, identifier):
  """
  Returns true if a request to mint or create an identifier is
  authorized.  'user' and 'group' should each be authenticated (local
  name, persistent identifier) tuples, e.g., ("dryad",
  "ark:/13030/foo").  'identifier' may be a complete identifier or
  just a shoulder; in either case it must be qualified, e.g.,
  "doi:10.5060/".  Throws an exception on error.
  """
  if any(map(lambda s: identifier.startswith(s.key), _getTestShoulders())):
    return True
  if any(map(lambda s: identifier.startswith(s.key), _getShoulders(group))):
    return True
  return False

def authorizeUpdate (rUser, rGroup, identifier, iUser, iGroup, iCoOwners,
  metadataElements):
  """
  Returns true if a request to update an existing identifier is
  authorized.  'rUser' and 'rGroup' identify the requester and should
  each be authenticated (local name, persistent identifier) tuples,
  e.g., ("dryad", "ark:/13030/foo"); 'iUser' and 'iGroup' should be
  similar quantities that identify the identifier's owner.
  'identifier' is the identifier in question; it must be qualified, as
  in "doi:10.5060/foo".  'iCoOwners' is a list of the identifier's
  co-owners; each co-owner should be a tuple as above.
  'metadataElements' is a list of the metadata elements being updated.
  Throws an exception on error.
  """
  if rUser[1] == iUser[1] or rUser[0] == _adminUsername:
    return True
  elif (rUser[0] in _getCoOwners(iUser[0]) or\
    rUser[1] in [co[1] for co in iCoOwners]) and\
    "_coowners" not in metadataElements:
    return True
  else:
    return False

def authorizeDelete (rUser, rGroup, identifier, iUser, iGroup, iCoOwners):
  """
  Returns true if a request to delete an existing identifier is
  authorized.  'rUser' and 'rGroup' identify the requester and should
  each be authenticated (local name, persistent identifier) tuples,
  e.g., ("dryad", "ark:/13030/foo"); 'iUser' and 'iGroup' should be
  similar quantities that identify the identifier's owner.
  'identifier' is the identifier in question; it must be qualified, as
  in "doi:10.5060/foo".  'iCoOwners' is a list of the identifier's
  co-owners; each co-owner should be a tuple as above.  Throws an
  exception on error.
  """
  if rUser[1] == iUser[1] or rUser[0] == _adminUsername:
    return True
  elif (rUser[0] in _getCoOwners(iUser[0]) or\
    rUser[1] in [co[1] for co in iCoOwners]):
    return True
  else:
    return False

def authorizeCrossref (user, group, identifier):
  return True
