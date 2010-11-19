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
import log

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
