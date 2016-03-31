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
import ezidadmin
import ezidapp.models.shoulder
import log
import useradmin
import util2

# Below, _groups maps groups (identified by 2- or 3-tuples; see NOTES)
# to 4-tuples (shoulders, crossrefEnabled, crossrefMail,
# crossrefSendMailOnError).  In the latter, 'shoulders' is a list of
# ezidapp.models.Shoulder objects.  'crossrefEnabled' and
# 'crossrefSendMailOnError' are booleans.  'crossrefMail' is a list of
# string email addresses.

_lock = threading.Lock()
_groups = None
_coOwners = None
_reverseCoOwners = None
_ldapEnabled = None
_ldapServer = None
_userDnTemplate = None
_adminUsername = None
_adminPassword = None

def _loadConfig ():
  global _groups, _coOwners, _reverseCoOwners, _ldapEnabled
  global _ldapServer, _userDnTemplate, _adminUsername, _adminPassword
  _lock.acquire()
  try:
    _groups = {}
    _coOwners = {}
    _reverseCoOwners = None
    _ldapEnabled = (config.get("ldap.enabled").lower() == "true")
    _ldapServer = config.get("ldap.server")
    _userDnTemplate = config.get("ldap.user_dn_template")
    _adminUsername = config.get("ldap.admin_username")
    _adminPassword = config.get("ldap.admin_password")
  finally:
    _lock.release()

_loadConfig()
config.registerReloadListener(_loadConfig)

def _lookupShoulders (group, shoulderText):
  if shoulderText == "NONE": return []
  l = []
  for s in shoulderText.split():
    try:
      so = ezidapp.models.shoulder.getExactMatch(s)
      assert so != None, "group '%s' has undefined shoulder: %s" %\
        (group[0], s)
      if so not in l: l.append(so)
    except AssertionError, e:
      log.otherError("policy._lookupShoulders", e)
  return l

def _loadGroupLdap (group):
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
    sl = _lookupShoulders(group, r[0][1]["shoulderList"][0].decode("UTF-8"))
    if "crossrefEnabled" in r[0][1]:
      ce = (r[0][1]["crossrefEnabled"][0].lower() == "true")
    else:
      ce = False
    if "crossrefMail" in r[0][1]:
      cml = [m.decode("UTF-8") for m in r[0][1]["crossrefMail"]]
    else:
      cml = []
    if "crossrefSendMailOnError" in r[0][1]:
      csm = (r[0][1]["crossrefSendMailOnError"][0].lower() == "true")
    else:
      csm = False
    return (sl, ce, cml, csm)
  finally:
    if l: l.unbind()

def _loadGroupLocal (group):
  return (_lookupShoulders(group,
    config.get("group_%s.shoulders" % group[0])),
    config.get("group_%s.crossref_enabled" % group[0]).lower() == "true",
    [m for m in config.get("group_%s.crossref_mail" % group[0]).split(",")\
    if len(m) > 0],
    config.get("group_%s.crossref_send_mail_on_error" % group[0]).\
    lower() == "true")

def _loadGroup (group):
  if group[0] == _adminUsername:
    return ([s for s in ezidapp.models.shoulder.getAll() if not s.isTest],
      True, [], False)
  elif group[0] == "anonymous":
    return ([], False, [], False)
  elif _ldapEnabled:
    return _loadGroupLdap(group)
  else:
    return _loadGroupLocal(group)

def _getShoulders (group):
  _lock.acquire()
  try:
    if group not in _groups: _groups[group] = _loadGroup(group)
    return _groups[group][0]
  finally:
    _lock.release()

def _getCrossrefInfo (group):
  _lock.acquire()
  try:
    if group not in _groups: _groups[group] = _loadGroup(group)
    return _groups[group][1:]
  finally:
    _lock.release()

def getShoulders (user, group):
  """
  Returns a list of the shoulders available to a user not including
  the test shoulders.  'user' and 'group' should each be authenticated
  (local name, persistent identifier) tuples, e.g., ("dryad",
  "ark:/13030/foo").  Each shoulder is described by an
  ezidapp.models.Shoulder object.  Throws an exception on error.
  """
  return _getShoulders(group)[:]

def getCrossrefInfo (user, group):
  """
  Returns a 3-tuple (crossrefEnabled, crossrefMail,
  crossrefSendMailOnError) for a user.  'user' and 'group' should each
  be authenticated (local name, persistent identifier) tuples, e.g.,
  ("dryad", "ark:/13030/foo").  'crossrefEnabled' and
  'crossrefSendMailOnError' are booleans.  'crossrefMail' is a list of
  string email addresses.  Throws an exception on error.
  """
  ci = _getCrossrefInfo(group)
  return (ci[0], ci[1][:], ci[2])

def clearGroupCache (group):
  """
  Clears the group cache for a group.  'group' should be a simple
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
  return [o for o in config.get("user_%s.co_owners" % user).split(",")\
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

def _loadReverseCoOwnersLdap ():
  try:
    d = {}
    l = ezidadmin.getUsers()
    assert type(l) is list, "ezidadmin.getUsers failed: " + l
    for u, col in [(r["uid"], r["ezidCoOwners"]) for r in l]:
      for co in re.split("[, ]+", col):
        if len(co) == 0: continue
        if co not in d: d[co] = []
        if u not in d[co]: d[co].append(u)
    return d
  except Exception, e:
    log.otherError("policy._loadReverseCoOwnersLdap", e)
    return {}

def _loadReverseCoOwnersLocal ():
  d = {}
  for u in config.get("users.keys").split(","):
    for co in config.get("user_%s.co_owners" % u).split(","):
      if len(co) == 0: continue
      if co not in d: d[co] = []
      if u not in d[co]: d[co].append(u)
  return d

def getReverseCoOwners (user):
  """
  Returns a list of other users that have named 'user' as an
  account-level co-owner.  I.e., if users A and B both name user
  'user' as an account-level co-owner, the return is [A, B].  All
  users are identified by local names.
  """
  global _reverseCoOwners
  _lock.acquire()
  try:
    if _reverseCoOwners is None:
      if _ldapEnabled:
        _reverseCoOwners = _loadReverseCoOwnersLdap()
      else:
        _reverseCoOwners = _loadReverseCoOwnersLocal()
    return _reverseCoOwners.get(user, [])
  finally:
    _lock.release()

def clearReverseCoOwnerCache ():
  """
  Clears the reverse co-ownership cache.
  """
  global _reverseCoOwners
  _lock.acquire()
  try:
    _reverseCoOwners = None
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
  if util2.isTestIdentifier(identifier): return True
  if any(map(lambda s: identifier.startswith(s.prefix), _getShoulders(group))):
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
  """
  Returns true if a request to register an identifier with CrossRef is
  authorized.  'user' and 'group' identify the requester and should
  each be authenticated (local name, persistent identifier) tuples,
  e.g., ("dryad", "ark:/13030/foo").  'identifier' is the identifier
  in question; it must be qualified, as in "doi:10.5060/foo".  Throws
  an exception on error.
  """
  s = ezidapp.models.shoulder.getLongestMatch(identifier)
  # Should never happen.
  assert s is not None, "shoulder not found"
  return (user[0] == _adminUsername or _getCrossrefInfo(group)[0]) and\
    identifier.startswith("doi:") and s.crossrefEnabled
