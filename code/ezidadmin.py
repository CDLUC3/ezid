# =============================================================================
#
# EZID :: ezidadmin.py
#
# EZID administrative support functions.
#
# Note: we use UTF-8 encoding/decoding for attribute values, but not
# for DNs.  RFC 4514 mentions using UTF-8 for DNs, but it also
# describes additional backslash escaping with the net effect that it
# appears that DNs reside entirely within the confines of ASCII (but
# we could be wrong on this point).
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

import config
import ezid
import log
import policy
import util

_ldapEnabled = None
_ldapServer = None
_baseDn = None
_userDnTemplate = None
_userDnPattern = None
_adminUsername = None
_adminPassword = None
_ldapAdminDn = None
_ldapAdminPassword = None
_shoulders = None
_agentPrefix = None

def _loadConfig ():
  global _ldapEnabled, _ldapServer, _baseDn, _userDnTemplate, _userDnPattern
  global _adminUsername, _adminPassword, _ldapAdminDn, _ldapAdminPassword
  global _shoulders, _agentPrefix
  _ldapEnabled = (config.config("ldap.enabled").lower() == "true")
  _ldapServer = config.config("ldap.server")
  _baseDn = config.config("ldap.base_dn")
  _userDnTemplate = config.config("ldap.user_dn_template")
  i = _userDnTemplate.find("%s")
  _userDnPattern = re.compile(re.escape(_userDnTemplate[:i]) + ".*" +\
    re.escape(_userDnTemplate[i+2:]) + "$")
  _adminUsername = config.config("ldap.admin_username")
  _adminPassword = config.config("ldap.admin_password")
  _ldapAdminDn = config.config("ldap.ldap_admin_dn")
  _ldapAdminPassword = config.config("ldap.ldap_admin_password")
  _shoulders = [k for k in config.config("prefixes.keys").split(",")\
    if not k.startswith("TEST")]
  _agentPrefix = config.config("prefix_cdlagent.prefix")
  assert _agentPrefix.startswith("ark:/")

_loadConfig()
config.addLoader(_loadConfig)

def _validateShoulderList (sl):
  # Returns a normalized shoulder list in string form, or None.
  l = []
  for s in re.split("[, ]+", sl):
    if len(s) == 0: continue
    if s not in _shoulders: return None
    if s not in l: l.append(s)
  if len(l) == 0: return None
  return ",".join(l)

def getEntries (usersOnly=False):
  """
  Returns a list of the DNs of all LDAP entries, or a string message
  if an error occurs.  If usersOnly is true, only entries whose DNs
  match the user DN template are returned.
  """
  if not _ldapEnabled: return "Functionality unavailable."
  l = None
  try:
    l = ldap.initialize(_ldapServer)
    l.bind_s(_userDnTemplate % _adminUsername, _adminPassword,
      ldap.AUTH_SIMPLE)
    # We don't want any attributes; setting attrlist to [] below
    # doesn't work for some reason, but setting it to [""] does.
    r = l.search_s(_baseDn, ldap.SCOPE_SUBTREE, attrlist=[""])
    return [v[0] for v in r if not usersOnly or _userDnPattern.match(v[0])]
  except Exception, e:
    log.otherError("ezidadmin.getEntries", e)
    return "Internal server error."
  finally:
    if l: l.unbind()

def getGroups ():
  """
  Returns a list of all EZID groups, or a string message if an error
  occurs.  Each group is represented as a dictionary with keys 'dn',
  'gid' (selected from LDAP attributes gid or uid), 'arkId' (selected
  from LDAP attributes groupArkId or arkId), 'shoulderList',
  'agreementOnFile' (a boolean), and 'users'.  The latter is a list of
  the group's users; each user is represented as a dictionary with
  keys 'dn' and 'uid'.  User lists are ordered by uid; the list of
  groups as a whole is ordered by gid.
  """
  if not _ldapEnabled: return "Functionality unavailable."
  l = None
  try:
    l = ldap.initialize(_ldapServer)
    l.bind_s(_userDnTemplate % _adminUsername, _adminPassword,
      ldap.AUTH_SIMPLE)
    r = l.search_s(_baseDn, ldap.SCOPE_SUBTREE, "(objectClass=ezidGroup)")
    groups = {}
    seenGids = set()
    seenArkIds = set()
    for dn, attrs in r:
      d = { "dn": dn }
      assert ("gid" in attrs or "uid" in attrs) and ("groupArkId" in attrs or\
        "arkId" in attrs) and "shoulderList" in attrs,\
        "missing required LDAP attribute, DN='%s'" % dn
      d["gid"] = attrs["gid" if "gid" in attrs else "uid"][0].decode("UTF-8")
      assert len(d["gid"]) > 0 and " " not in d["gid"],\
        "invalid gid, DN='%s'" % dn
      assert d["gid"] not in seenGids, "duplicate gid, DN='%s'" % dn
      seenGids.add(d["gid"])
      d["arkId"] = attrs["groupArkId" if "groupArkId" in attrs else "arkId"]\
        [0].decode("UTF-8")
      assert d["arkId"].startswith("ark:/") and\
        d["arkId"][5:] == util.validateArk(d["arkId"][5:]),\
        "invalid ARK identifier, DN='%s'" % dn
      assert d["arkId"] not in seenArkIds,\
        "duplicate ARK identifier, DN='%s'" % dn
      seenArkIds.add(d["arkId"])
      d["shoulderList"] = attrs["shoulderList"][0].decode("UTF-8")
      if d["gid"] == _adminUsername:
        assert d["shoulderList"] == "*", "invalid admin shoulder list"
      else:
        d["shoulderList"] = _validateShoulderList(d["shoulderList"])
        assert d["shoulderList"] != None, "invalid shoulder list, DN='%s'" % dn
      if "agreementOnFile" in attrs:
        d["agreementOnFile"] = (attrs["agreementOnFile"][0].lower() == "true")
      else:
        d["agreementOnFile"] = False
      d["users"] = []
      groups[dn] = d
    r = l.search_s(_baseDn, ldap.SCOPE_SUBTREE, "(objectClass=ezidUser)",
      attrlist=["uid", "ezidOwnerGroup"])
    seenUids = set()
    for dn, attrs in r:
      assert "uid" in attrs and "ezidOwnerGroup" in attrs,\
        "missing required LDAP attribute, DN='%s'" % dn
      uid = attrs["uid"][0].decode("UTF-8")
      assert len(uid) > 0 and " " not in uid, "invalid uid, DN='%s'" % dn
      assert uid not in seenUids, "duplicate uid, DN='%s'" % dn
      seenUids.add(uid)
      groupDn = attrs["ezidOwnerGroup"][0]
      assert groupDn in groups,\
        "user references nonexistent group, DN='%s'" % dn
      groups[groupDn]["users"].append({ "dn": dn, "uid": uid })
    groups = groups.values()
    for g in groups: g["users"].sort(key=lambda u: u["uid"])
    groups.sort(key=lambda g: g["gid"])
    return groups
  except Exception, e:
    log.otherError("ezidadmin.getGroups", e)
    return "Internal server error."
  finally:
    if l: l.unbind()

def getUsers ():
  """
  Returns a list of all EZID users, or a string message if an error
  occurs.  Each user is represented as a dictionary with keys 'dn',
  'uid', 'arkId', 'groupDn', and 'groupGid'.  The list is ordered by
  uid.
  """
  if not _ldapEnabled: return "Functionality unavailable."
  l = None
  try:
    l = ldap.initialize(_ldapServer)
    l.bind_s(_userDnTemplate % _adminUsername, _adminPassword,
      ldap.AUTH_SIMPLE)
    r = l.search_s(_baseDn, ldap.SCOPE_SUBTREE, "(objectClass=ezidGroup)",
      attrlist=["gid", "uid", "groupArkId", "arkId"])
    groups = {}
    seenGids = set()
    seenArkIds = set()
    for dn, attrs in r:
      assert ("gid" in attrs or "uid" in attrs) and ("groupArkId" in attrs or\
        "arkId" in attrs), "missing required LDAP attribute, DN='%s'" % dn
      gid = attrs["gid" if "gid" in attrs else "uid"][0].decode("UTF-8")
      assert len(gid) > 0 and " " not in gid, "invalid gid, DN='%s'" % dn
      assert gid not in seenGids, "duplicate gid, DN='%s'" % dn
      seenGids.add(gid)
      arkId = attrs["groupArkId" if "groupArkId" in attrs else "arkId"][0]\
        .decode("UTF-8")
      assert arkId not in seenArkIds, "duplicate ARK identifier, DN='%s'" % dn
      seenArkIds.add(arkId)
      groups[dn] = gid
    r = l.search_s(_baseDn, ldap.SCOPE_SUBTREE, "(objectClass=ezidUser)",
      attrlist=["uid", "arkId", "ezidOwnerGroup"])
    users = []
    seenUids = set()
    for dn, attrs in r:
      d = { "dn": dn }
      assert "uid" in attrs and "arkId" in attrs and\
        "ezidOwnerGroup" in attrs,\
        "missing required LDAP attribute, DN='%s'" % dn
      d["uid"] = attrs["uid"][0].decode("UTF-8")
      assert len(d["uid"]) > 0 and " " not in d["uid"],\
        "invalid uid, DN='%s'" % dn
      assert d["uid"] not in seenUids, "duplicate uid, DN='%s'" % dn
      seenUids.add(d["uid"])
      d["arkId"] = attrs["arkId"][0].decode("UTF-8")
      assert d["arkId"].startswith("ark:/") and\
        d["arkId"][5:] == util.validateArk(d["arkId"][5:]),\
        "invalid ARK identifier, DN='%s'" % dn
      assert d["arkId"] not in seenArkIds,\
        "duplicate ARK identifier, DN='%s'" % dn
      seenArkIds.add(d["arkId"])
      d["groupDn"] = attrs["ezidOwnerGroup"][0]
      assert d["groupDn"] in groups,\
        "user references nonexistent group, DN='%s'" % dn
      d["groupGid"] = groups[d["groupDn"]]
      users.append(d)
    users.sort(key=lambda u: u["uid"])
    return users
  except Exception, e:
    log.otherError("ezidadmin.getUsers", e)
    return "Internal server error."
  finally:
    if l: l.unbind()

def makeGroup (dn, gid, agreementOnFile, shoulderList, user, group):
  """
  Makes an existing LDAP entry an EZID group, returning None on
  success or a string message on error.  'dn' should be the entry's
  DN; the entry must not already be an EZID group, nor may it already
  have any EZID group attributes (gid, groupArkId, agreementOnFile, or
  shoulderList).  'user' and 'group' are used in identifier creation
  and modification; each should be authenticated (local name,
  persistent identifier) tuples, e.g., ("dryad", "ark:/13030/foo").
  """
  if not _ldapEnabled: return "Functionality unavailable."
  if len(dn) == 0: return "LDAP entry required."
  if len(gid) == 0: return "Group name required."
  if " " in gid: return "Invalid group name."
  if len(shoulderList) == 0: return "Shoulder list required."
  shoulderList = _validateShoulderList(shoulderList)
  if shoulderList == None: return "Unrecognized shoulder."
  groups = getGroups()
  if type(groups) is str: return groups
  if gid in [g["gid"] for g in groups]: return "Group name is already in use."
  l = None
  try:
    l = ldap.initialize(_ldapServer)
    # The modify operation below requires binding as a privileged LDAP
    # user.
    l.bind_s(_ldapAdminDn, _ldapAdminPassword, ldap.AUTH_SIMPLE)
    try:
      r = l.search_s(dn, ldap.SCOPE_BASE, attrlist=["objectClass", "gid",
        "groupArkId", "agreementOnFile", "shoulderList"])
    except ldap.INVALID_DN_SYNTAX:
      return "Invalid DN."
    except ldap.NO_SUCH_OBJECT:
      return "No such LDAP entry."
    if "ezidGroup" in r[0][1]["objectClass"]:
      return "LDAP entry is already an EZID group."
    assert "gid" not in r[0][1] and "groupArkId" not in r[0][1] and\
      "agreementOnFile" not in r[0][1] and "shoulderList" not in r[0][1],\
      "unexpected LDAP attribute, DN='%s'" % dn
    r = ezid.mintIdentifier(_agentPrefix, user, group)
    if r.startswith("success:"):
      arkId = r.split()[1]
    else:
      assert False, "ezid.mintIdentifier failed: " + r
    r = ezid.setMetadata(arkId, user, group,
      { "_profile": "erc", "erc.who": dn, "erc.what": "EZID group" })
    assert r.startswith("success:"), "ezid.setMetadata failed: " + r
    l.modify_s(dn, [(ldap.MOD_ADD, "objectClass", "ezidGroup"),
      (ldap.MOD_ADD, "gid", gid.encode("UTF-8")),
      (ldap.MOD_ADD, "groupArkId", arkId.encode("UTF-8")),
      (ldap.MOD_ADD, "agreementOnFile",
        "true" if agreementOnFile else "false"),
      (ldap.MOD_ADD, "shoulderList", shoulderList.encode("UTF-8"))])
    return None
  except Exception, e:
    log.otherError("ezidadmin.makeGroup", e)
    return "Internal server error."
  finally:
    if l: l.unbind()

def updateGroup (dn, agreementOnFile, shoulderList):
  """
  Updates an EZID group, returning None on success or a string message
  on error.  'dn' should be the group's LDAP entry's DN.
  """
  if not _ldapEnabled: return "Functionality unavailable."
  if len(shoulderList) == 0: return "Shoulder list required."
  shoulderList = _validateShoulderList(shoulderList)
  if shoulderList == None: return "Unrecognized shoulder."
  l = None
  try:
    l = ldap.initialize(_ldapServer)
    # The modify operation below requires binding as a privileged LDAP
    # user.
    l.bind_s(_ldapAdminDn, _ldapAdminPassword, ldap.AUTH_SIMPLE)
    try:
      r = l.search_s(dn, ldap.SCOPE_BASE, attrlist=["objectClass",
        "agreementOnFile", "shoulderList", "uid", "gid"])
    except ldap.NO_SUCH_OBJECT:
      # UI controls should prevent this from ever happening.
      return "No such LDAP entry."
    if "ezidGroup" not in r[0][1]["objectClass"]:
      # Ditto.
      return "LDAP entry is not an EZID group."
    assert "shoulderList" in r[0][1] and\
      ("gid" in r[0][1] or "uid" in r[0][1]),\
      "missing required LDAP attribute, DN='%s'" % dn
    l.modify_s(dn,
      [(ldap.MOD_REPLACE, "shoulderList", shoulderList.encode("UTF-8")),
      (ldap.MOD_REPLACE if "agreementOnFile" in r[0][1] else ldap.MOD_ADD,
      "agreementOnFile", "true" if agreementOnFile else "false")])
    oldShoulderList = r[0][1]["shoulderList"][0].decode("UTF-8")
    if shoulderList != oldShoulderList:
      if "gid" in r[0][1]:
        gid = r[0][1]["gid"][0].decode("UTF-8")
      else:
        gid = r[0][1]["uid"][0].decode("UTF-8")
      policy.clearPrefixCache(gid)
    return None
  except Exception, e:
    log.otherError("ezidadmin.updateGroup", e)
    return "Internal server error."
  finally:
    if l: l.unbind()

def makeUser (dn, groupDn, user, group):
  """
  Makes an existing LDAP entry an EZID user, returning None on success
  or a string message on error.  'dn' should be the entry's DN.  The
  entry must not already be an EZID user; must already have a uid
  attribute; must not already have an ezidOwnerGroup attribute; and
  may already have an arkId attribute.  'groupDn' should be the new
  user's EZID group's LDAP entry's DN.  'user' and 'group' are used in
  identifier creation and modification; each should be authenticated
  (local name, persistent identifier) tuples, e.g., ("dryad",
  "ark:/13030/foo").
  """
  if not _ldapEnabled: return "Functionality unavailable."
  if len(dn) == 0: return "LDAP entry required."
  if not _userDnPattern.match(dn): return "DN does not match user template."
  l = None
  try:
    l = ldap.initialize(_ldapServer)
    # The modify operation below requires binding as a privileged LDAP
    # user.
    l.bind_s(_ldapAdminDn, _ldapAdminPassword, ldap.AUTH_SIMPLE)
    try:
      r = l.search_s(groupDn, ldap.SCOPE_BASE, attrlist=["objectClass"])
    except ldap.NO_SUCH_OBJECT:
      # UI controls should prevent this from ever happening.
      return "No such group LDAP entry."
    if "ezidGroup" not in r[0][1]["objectClass"]:
      # Ditto.
      return "Group LDAP entry is not an EZID group."
    try:
      r = l.search_s(dn, ldap.SCOPE_BASE, attrlist=["objectClass", "uid",
        "arkId", "ezidOwnerGroup"])
    except ldap.INVALID_DN_SYNTAX:
      return "Invalid DN."
    except ldap.NO_SUCH_OBJECT:
      return "No such LDAP entry."
    if "ezidUser" in r[0][1]["objectClass"]:
      return "LDAP entry is already an EZID user."
    if "uid" not in r[0][1]: return "LDAP entry lacks a uid attribute."
    if " " in r[0][1]["uid"][0].decode("UTF-8"):
      return "LDAP entry's uid is invalid."
    assert "ezidOwnerGroup" not in r[0][1],\
      "unexpected LDAP attribute, DN='%s'" % dn
    if "arkId" in r[0][1]:
      arkId = r[0][1]["arkId"][0].decode("UTF-8")
      if not arkId.startswith(_agentPrefix) or\
        arkId[5:] != util.validateArk(arkId[5:]):
        return "LDAP entry has invalid ARK identifier."
      r = ezid.getMetadata(arkId)
      assert type(r) is tuple, "ezid.getMetadata failed: " + r
      if "erc.what" in r[1] and len(r[1]["erc.what"].strip()) > 0:
        what = r[1]["erc.what"].strip() + "\nEZID user"
      else:
        what = "EZID user"
      r = ezid.setMetadata(arkId, user, group,
        { "_profile": "erc", "erc.who": dn, "erc.what": what })
      assert r.startswith("success:"), "ezid.setMetadata failed: " + r
      m = []
    else:
      r = ezid.mintIdentifier(_agentPrefix, user, group)
      if r.startswith("success:"):
        arkId = r.split()[1]
      else:
        assert False, "ezid.mintIdentifier failed: " + r
      r = ezid.setMetadata(arkId, user, group,
        { "_profile": "erc", "erc.who": dn, "erc.what": "EZID user" })
      assert r.startswith("success:"), "ezid.setMetadata failed: " + r
      m = [(ldap.MOD_ADD, "arkId", arkId.encode("UTF-8"))]
    m += [(ldap.MOD_ADD, "objectClass", "ezidUser"),
      (ldap.MOD_ADD, "ezidOwnerGroup", groupDn.encode("UTF-8"))]
    l.modify_s(dn, m)
    return None
  except Exception, e:
    log.otherError("ezidadmin.makeUser", e)
    return "Internal server error."
  finally:
    if l: l.unbind()
