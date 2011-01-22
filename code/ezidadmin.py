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
import log
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

def _loadConfig ():
  global _ldapEnabled, _ldapServer, _baseDn, _userDnTemplate, _userDnPattern
  global _adminUsername, _adminPassword, _ldapAdminDn, _ldapAdminPassword
  global _shoulders
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
  return "TBD"

def updateGroup (dn, agreementOnFile, shoulderList):
  return "TBD"

def makeUser (dn, groupDn, user, group):
  return "TBD"
