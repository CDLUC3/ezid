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
import re
import threading

import config
import useradmin

_lock = threading.Lock()
_prefixes = None
_nonTestLabels = None
_groups = None
_coOwners = None
_ldapEnabled = None
_ldapServer = None
_userDnTemplate = None
_adminUsername = None
_adminPassword = None

def _loadConfig ():
  global _prefixes, _nonTestLabels, _groups, _coOwners, _ldapEnabled
  global _ldapServer, _userDnTemplate, _adminUsername, _adminPassword
  _lock.acquire()
  try:
    _prefixes = dict([k, config.config("prefix_%s.prefix" % k)]\
      for k in config.config("prefixes.keys").split(","))
    _nonTestLabels = ",".join(k for k in\
      config.config("prefixes.keys").split(",") if not k.startswith("TEST"))
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

def _loadPrefixesLdap (group):
  l = None
  try:
    l = ldap.initialize(_ldapServer)
    l.bind_s(_userDnTemplate % _adminUsername, _adminPassword,
      ldap.AUTH_SIMPLE)
    r = l.search_s(group[2], ldap.SCOPE_BASE)
    assert len(r) == 1 and r[0][0] == group[2] and\
      "ezidGroup" in r[0][1]["objectClass"] and\
      len(r[0][1]["shoulderList"]) == 1,\
      "unexpected return from LDAP search command, DN='%s'" % group[2]
    # Although not documented anywhere, it appears that returned
    # values are UTF-8 encoded.
    return r[0][1]["shoulderList"][0].decode("UTF-8")
  finally:
    if l: l.unbind()

def _loadPrefixesLocal (group):
  return config.config("group_%s.prefixes" % group[0])

def _loadPrefixes (group):
  if group[0] == _adminUsername:
    l = _nonTestLabels
  elif group[0] == "anonymous":
    l = ""
  elif _ldapEnabled:
    l = _loadPrefixesLdap(group)
  else:
    l = _loadPrefixesLocal(group)
  return [_prefixes[k] for k in re.split("[, ]+", l) if len(k) > 0]

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
  (local name, persistent identifier) tuples, e.g., ("dryad",
  "ark:/13030/foo").  Throws an exception on error.
  """
  return _getPrefixes(group)[:]

def clearPrefixCache (group):
  """
  Clears the prefix cache for a group.  'group' should be a simple
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

def _loadCoOwnersLdap (user):
  l = None
  try:
    l = ldap.initialize(_ldapServer)
    l.bind_s(_userDnTemplate % _adminUsername, _adminPassword,
      ldap.AUTH_SIMPLE)
    dn = _userDnTemplate % ldap.dn.escape_dn_chars(user)
    r = l.search_s(dn, ldap.SCOPE_BASE, attrlist=["objectClass",
      "ezidCoOwners"])
    assert len(r) == 1 and r[0][0] == dn and\
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

def authorizeCreate (user, group, prefix):
  """
  Returns true if a request to mint or create an identifier is
  authorized.  'user' and 'group' should each be authenticated (local
  name, persistent identifier) tuples, e.g., ("dryad",
  "ark:/13030/foo").  'prefix' may be a complete identifier or just a
  prefix of one; in either case it must be qualified, e.g.,
  "doi:10.5060/".  Throws an exception on error.
  """
  if prefix.startswith(_prefixes["TESTARK"]): return True
  if prefix.startswith(_prefixes["TESTDOI"]): return True
  if any(map(lambda p: prefix.startswith(p), _getPrefixes(group))): return True
  return False

def authorizeUpdate (rUser, rGroup, identifier, iUser, iGroup):
  """
  Returns true if a request to update an existing identifier is
  authorized.  'rUser' and 'rGroup' identify the requester and should
  each be authenticated (local name, persistent identifier) tuples,
  e.g., ("dryad", "ark:/13030/foo"); 'iUser' and 'iGroup' should be
  similar quantities that identify the identifier's owner.
  'identifier' is the identifier in question; it must be qualified, as
  in "doi:10.5060/foo".  Throws an exception on error.
  """
  if rUser[1] == iUser[1]: return True
  if rUser[0] == _adminUsername: return True
  if rUser[0] in _getCoOwners(iUser[0]): return True
  return False
