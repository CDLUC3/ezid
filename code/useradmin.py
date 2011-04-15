# =============================================================================
#
# EZID :: useradmin.py
#
# User profile administration.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2010, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.conf
import django.core.mail
import hashlib
import ldap
import ldap.dn
import re
import time
import urllib

import config
import ezid
import idmap
import log
import policy

_ezidUrl = None
_ldapEnabled = None
_ldapServer = None
_userDnTemplate = None
_adminUsername = None
_adminPassword = None
_ldapAdminDn = None
_ldapAdminPassword = None

def _loadConfig ():
  global _ezidUrl, _ldapEnabled, _ldapServer, _userDnTemplate
  global _adminUsername, _adminPassword, _ldapAdminDn, _ldapAdminPassword
  _ezidUrl = config.config("DEFAULT.ezid_base_url")
  _ldapEnabled = (config.config("ldap.enabled").lower() == "true")
  _ldapServer = config.config("ldap.server")
  _userDnTemplate = config.config("ldap.user_dn_template")
  _adminUsername = config.config("ldap.admin_username")
  _adminPassword = config.config("ldap.admin_password")
  _ldapAdminDn = config.config("ldap.ldap_admin_dn")
  _ldapAdminPassword = config.config("ldap.ldap_admin_password")

_loadConfig()
config.addLoader(_loadConfig)

def sendPasswordResetEmail (username, emailAddress):
  """
  Sends an email containing a password reset request link.  Returns
  None on success or a string message on error.
  """
  if not _ldapEnabled: return "Functionality unavailable."
  l = None
  try:
    l = ldap.initialize(_ldapServer)
    l.bind_s(_userDnTemplate % _adminUsername, _adminPassword,
      ldap.AUTH_SIMPLE)
    dn = _userDnTemplate % ldap.dn.escape_dn_chars(username)
    try:
      r = l.search_s(dn, ldap.SCOPE_BASE)
    except ldap.NO_SUCH_OBJECT:
      return "No such user."
    assert len(r) == 1 and r[0][0] == dn,\
      "unexpected return from LDAP search command, DN='%s'" % dn
    if "ezidUser" not in r[0][1]["objectClass"]: return "No such user."
    if "mail" not in r[0][1] or\
      r[0][1]["mail"][0].lower() != emailAddress.lower():
      return "Email address does not match address registered for username."
    t = int(time.time())
    hash = hashlib.sha1("%s|%d|%s" % (username, t,
      django.conf.settings.SECRET_KEY)).hexdigest()[::4]
    link = "%s/pwreset/%s,%d,%s" % (_ezidUrl, urllib.quote(username), t, hash)
    message = "You have requested to reset your EZID password.\n" +\
      "Click the link below to complete the process:\n\n" +\
      link + "\n\n" +\
      "Please do not reply to this email.\n"
    django.core.mail.send_mail("EZID password reset request", message,
      django.conf.settings.SERVER_EMAIL, [emailAddress])
    return None
  except Exception, e:
    log.otherError("useradmin.sendPasswordResetEmail", e)
    return "Internal server error."
  finally:
    if l: l.unbind()

def decodePasswordResetRequest (request):
  """
  Decodes a password reset request, returning a tuple (username,
  timestamp) on success or None on error.
  """
  m = re.match("/([^ ,]+),(\d+),([\da-f]+)$", request)
  if not m: return None
  username = m.group(1)
  t = m.group(2)
  hash = m.group(3)
  if hashlib.sha1("%s|%s|%s" % (username, t,
    django.conf.settings.SECRET_KEY)).hexdigest()[::4] != hash: return None
  return (username, int(t))

def resetPassword (username, password):
  """
  Resets a user's password.  Returns None on success or a string
  message on error.
  """
  if not _ldapEnabled: return "Functionality unavailable."
  l = None
  try:
    l = ldap.initialize(_ldapServer)
    # This operation requires binding as a privileged LDAP user.
    l.bind_s(_ldapAdminDn, _ldapAdminPassword, ldap.AUTH_SIMPLE)
    dn = _userDnTemplate % ldap.dn.escape_dn_chars(username)
    try:
      r = l.search_s(dn, ldap.SCOPE_BASE)
    except ldap.NO_SUCH_OBJECT:
      return "No such user."
    assert len(r) == 1 and r[0][0] == dn,\
      "unexpected return from LDAP search command, DN='%s'" % dn
    if "ezidUser" not in r[0][1]["objectClass"]: return "No such user."
    l.passwd_s(dn, None, password)
    return None
  except Exception, e:
    log.otherError("useradmin.resetPassword", e)
    return "Internal server error."
  finally:
    if l: l.unbind()

def getAccountProfile (username):
  """
  Returns a user's account profile as a dictionary keyed by LDAP
  attribute names.  Returns a string message on error.
  """
  if not _ldapEnabled: return "Functionality unavailable."
  l = None
  try:
    l = ldap.initialize(_ldapServer)
    l.bind_s(_userDnTemplate % _adminUsername, _adminPassword,
      ldap.AUTH_SIMPLE)
    dn = _userDnTemplate % ldap.dn.escape_dn_chars(username)
    r = l.search_s(dn, ldap.SCOPE_BASE)
    assert len(r) == 1 and r[0][0] == dn,\
      "unexpected return from LDAP search command, DN='%s'" % dn
    assert "ezidUser" in r[0][1]["objectClass"],\
      "not an EZID user, DN='%s'" % dn
    if "ezidCoOwners" in r[0][1]:
      # Although not documented anywhere, it appears that returned
      # values are UTF-8 encoded.
      return { "ezidCoOwners": r[0][1]["ezidCoOwners"][0].decode("UTF-8") }
    else:
      return {}
  except Exception, e:
    log.otherError("useradmin.getAccountProfile", e)
    return "Internal server error."
  finally:
    if l: l.unbind()

def getContactInfo (username):
  """
  Returns a user's contact information as a dictionary keyed by LDAP
  attribute names.  Returns a string message on error.
  """
  if not _ldapEnabled: return "Functionality unavailable."
  l = None
  try:
    l = ldap.initialize(_ldapServer)
    l.bind_s(_userDnTemplate % _adminUsername, _adminPassword,
      ldap.AUTH_SIMPLE)
    dn = _userDnTemplate % ldap.dn.escape_dn_chars(username)
    r = l.search_s(dn, ldap.SCOPE_BASE)
    assert len(r) == 1 and r[0][0] == dn,\
      "unexpected return from LDAP search command, DN='%s'" % dn
    assert "ezidUser" in r[0][1]["objectClass"],\
      "not an EZID user, DN='%s'" % dn
    p = {}
    for a in ["givenName", "sn", "mail", "telephoneNumber"]:
      if a in r[0][1]:
        # Although not documented anywhere, it appears that returned
        # values are UTF-8 encoded.
        p[a] = r[0][1][a][0].decode("UTF-8")
      else:
        p[a] = ""
    return p
  except Exception, e:
    log.otherError("useradmin.getContactInfo", e)
    return "Internal server error."
  finally:
    if l: l.unbind()

def validateCoOwnerList (l, coOwnerList):
  """
  Validates and normalizes a co-owner list and converts it from string
  to list form.  Returns None if a username in the list does not exist
  or exists but is not an EZID user.  May also throw an exception.
  'l' should be an open LDAP connection.
  """
  col = []
  for o in re.split("[, ]+", coOwnerList):
    if len(o) == 0: continue
    try:
      dn = _userDnTemplate % ldap.dn.escape_dn_chars(o)
      r = l.search_s(dn, ldap.SCOPE_BASE, attrlist=["objectClass"])
      if "ezidUser" not in r[0][1]["objectClass"]: return None
    except ldap.NO_SUCH_OBJECT:
      return None
    if o not in col: col.append(o)
  return col

def _cacheLdapInformation (l, dn, arkId):
  attrs = l.search_s(dn, ldap.SCOPE_BASE)[0][1]
  d = {}
  for a in attrs:
    if a != "userPassword":
      d["ldap." + a] = " ; ".join(v.decode("UTF-8") for v in attrs[a])
  # We're assuming here that the EZID administrator user and group
  # names are identical.
  user = (_adminUsername, idmap.getUserId(_adminUsername))
  group = (_adminUsername, idmap.getGroupId(_adminUsername))
  r = ezid.setMetadata(arkId, user, group, d)
  assert r.startswith("success:"), "ezid.setMetadata failed: " + r

def setAccountProfile (username, coOwnerList):
  """
  Sets a user's account profile.  Returns None on success or a string
  message on error.
  """
  if not _ldapEnabled: return "Functionality unavailable."
  l = None
  try:
    l = ldap.initialize(_ldapServer)
    # This operation requires binding as a privileged LDAP user.
    l.bind_s(_ldapAdminDn, _ldapAdminPassword, ldap.AUTH_SIMPLE)
    dn = _userDnTemplate % ldap.dn.escape_dn_chars(username)
    r = l.search_s(dn, ldap.SCOPE_BASE, attrlist=["objectClass", "arkId",
      "ezidCoOwners"])
    assert len(r) == 1 and r[0][0] == dn,\
      "unexpected return from LDAP search command, DN='%s'" % dn
    assert "ezidUser" in r[0][1]["objectClass"],\
      "not an EZID user, DN='%s'" % dn
    assert "arkId" in r[0][1], "missing required LDAP attribute, DN='%s'" % dn
    arkId = r[0][1]["arkId"][0].decode("UTF-8")
    coOwnerList = validateCoOwnerList(l, coOwnerList)
    if coOwnerList is None: return "No such EZID user."
    if len(coOwnerList) > 0:
      m = [(ldap.MOD_REPLACE if "ezidCoOwners" in r[0][1] else\
        ldap.MOD_ADD, "ezidCoOwners", ",".join(coOwnerList).encode("UTF-8"))]
    else:
      if "ezidCoOwners" in r[0][1]:
        m = [(ldap.MOD_DELETE, "ezidCoOwners", None)]
      else:
        m = []
    if len(m) > 0: l.modify_s(dn, m)
    policy.clearCoOwnerCache(username)
    _cacheLdapInformation(l, dn, arkId)
    return None
  except Exception, e:
    log.otherError("useradmin.setAccountProfile", e)
    return "Internal server error."
  finally:
    if l: l.unbind()

def setContactInfo (username, d):
  """
  Sets a user's contact information.  'd' should be a dictionary that
  maps LDAP attribute names to values.  Note that if either of the
  LDAP attributes givenName or sn is supplied, then both should be,
  and a new value for cn will be computed and set as well.  Returns
  None on success or a string message on error.
  """
  if not _ldapEnabled: return "Functionality unavailable."
  if "givenName" in d:
    assert "sn" in d
    d["cn"] = (d["givenName"] + " " + d["sn"]).strip()
  else:
    assert "sn" not in d
  l = None
  try:
    l = ldap.initialize(_ldapServer)
    # This operation requires binding as a privileged LDAP user.
    l.bind_s(_ldapAdminDn, _ldapAdminPassword, ldap.AUTH_SIMPLE)
    dn = _userDnTemplate % ldap.dn.escape_dn_chars(username)
    r = l.search_s(dn, ldap.SCOPE_BASE)
    assert len(r) == 1 and r[0][0] == dn,\
      "unexpected return from LDAP search command, DN='%s'" % dn
    assert "ezidUser" in r[0][1]["objectClass"],\
      "not an EZID user, DN='%s'" % dn
    assert "arkId" in r[0][1], "missing required LDAP attribute, DN='%s'" % dn
    arkId = r[0][1]["arkId"][0].decode("UTF-8")
    m = []
    for a, v in d.items():
      # Although not documented anywhere, it appears that attribute
      # values are UTF-8 encoded.
      v = v.encode("UTF-8")
      if v != "":
        if a in r[0][1]:
          if len(r[0][1][a]) != 1 or v != r[0][1][a][0]:
            m.append((ldap.MOD_REPLACE, a, v))
        else:
          m.append((ldap.MOD_ADD, a, v))
      else:
        if a in r[0][1]: m.append((ldap.MOD_DELETE, a, None))
    try:
      if len(m) > 0: l.modify_s(dn, m)
    except ldap.INVALID_SYNTAX:
      return "Invalid syntax."
    _cacheLdapInformation(l, dn, arkId)
    return None
  except Exception, e:
    log.otherError("useradmin.setContactInfo", e)
    return "Internal server error."
  finally:
    if l: l.unbind()

def setPassword (username, old, new):
  """
  Sets a user's password.  Returns None on success or a string message
  on error.
  """
  if not _ldapEnabled: return "Functionality unavailable."
  l = None
  try:
    l = ldap.initialize(_ldapServer)
    dn = _userDnTemplate % ldap.dn.escape_dn_chars(username)
    try:
      l.bind_s(dn, old, ldap.AUTH_SIMPLE)
      l.passwd_s(dn, old, new)
    except ldap.INVALID_CREDENTIALS:
      return "Incorrect current password."
    return None
  except Exception, e:
    log.otherError("useradmin.setPassword", e)
    return "Internal server error."
  finally:
    if l: l.unbind()
