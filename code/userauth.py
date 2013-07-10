# =============================================================================
#
# EZID :: userauth.py
#
# User authentication.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2010, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import base64
import django.conf
import ldap
import re
import threading

import config
import log
import util

_ldapEnabled = None
_ldapServer = None
_lock = threading.Lock()
_ldapCache = None
_userDnTemplate = None
_users = None

def _loadConfig ():
  global _ldapEnabled, _ldapServer, _ldapCache, _userDnTemplate, _users
  _ldapEnabled = (config.config("ldap.enabled").lower() == "true")
  _ldapServer = config.config("ldap.server")
  _lock.acquire()
  _ldapCache = {}
  _lock.release()
  _userDnTemplate = config.config("ldap.user_dn_template")
  groupIds = dict([k, config.config("group_%s.id" % k)]\
    for k in config.config("groups.keys").split(","))
  _users = dict([k, (config.config("user_%s.password" % k),
    config.config("user_%s.id" % k), config.config("user_%s.group" % k),
    groupIds[config.config("user_%s.group" % k)])]\
    for k in config.config("users.keys").split(","))

_loadConfig()
config.addLoader(_loadConfig)

class AuthenticatedUser (object):
  """
  Describes an authenticated user.  Instance variables 'user' and
  'group' are each (local name, persistent identifier [, dn]) tuples,
  e.g., ("dryad", "ark:/13030/foo",
  "uid=dryad,ou=People,ou=uc3,dc=cdlib,dc=org").  Note that the last
  tuple component is present only when using LDAP authentication.
  """
  def __init__ (self, user, group):
    self.user = user
    self.group = group

# Escaping and encoding of DN attribute values per RFC 2253.
_pattern = re.compile("[,=+<>#;\\\\\"]")
def _escape (v):
  return _pattern.sub(lambda c: "\\" + c.group(0), v.encode("UTF-8"))

def _getAttributes (server, dn):
  r = server.search_s(dn, ldap.SCOPE_BASE)
  assert len(r) == 1 and r[0][0].lower() == dn.lower(),\
    "unexpected return from LDAP search command, DN='%s'" % dn
  r = r[0][1]
  # Although not documented anywhere, it appears that returned values
  # are UTF-8 encoded.
  for a in r: r[a] = [v.decode("UTF-8") for v in r[a]]
  # Clean up the single-valued attributes we care about.
  for a in ["arkId", "ezidOwnerGroup", "gid", "groupArkId", "uid"]:
    if a in r:
      assert len(r[a]) == 1,\
        "unexpected return from LDAP search command, DN='%s'" % dn
      r[a] = r[a][0]
  return r

def _authenticateLdap (username, password):
  l = None
  try:
    l = ldap.initialize(_ldapServer)
    userDn = _userDnTemplate % _escape(username)
    try:
      l.bind_s(userDn, password, ldap.AUTH_SIMPLE)
    except ldap.INVALID_CREDENTIALS:
      return None
    except ldap.UNWILLING_TO_PERFORM:
      # E.g., server won't accept empty password.
      return None
    _lock.acquire()
    try:
      if username in _ldapCache: return _ldapCache[username]
    finally:
      _lock.release()
    ua = _getAttributes(l, userDn)
    if "ezidUser" not in ua["objectClass"]: return None
    uid = ua["uid"]
    assert " " not in uid, "invalid character in uid, DN='%s'" % userDn
    userArkId = ua["arkId"]
    assert userArkId.startswith("ark:/") and\
      util.validateArk(userArkId[5:]) == userArkId[5:],\
      "invalid ARK identifier, DN='%s'" % userDn
    groupDn = ua["ezidOwnerGroup"]
    ga = _getAttributes(l, groupDn)
    assert "ezidGroup" in ga["objectClass"],\
      "invalid owner group, DN='%s'" % userDn
    if "gid" in ga:
      gid = ga["gid"]
    else:
      gid = ga["uid"]
    assert " " not in gid, "invalid character in gid, DN='%s'" % groupDn
    if "groupArkId" in ga:
      groupArkId = ga["groupArkId"]
    else:
      groupArkId = ga["arkId"]
    assert groupArkId.startswith("ark:/") and\
      util.validateArk(groupArkId[5:]) == groupArkId[5:],\
      "invalid ARK identifier, DN='%s'" % groupDn
    assert userArkId != groupArkId,\
      "overloaded ARK identifier, DN='%s'" % userDn
    au = AuthenticatedUser((uid, userArkId, userDn),
      (gid, groupArkId, groupDn))
    _lock.acquire()
    try:
      _ldapCache[username] = au
    finally:
      _lock.release()
    return au
  except Exception, e:
    log.otherError("userauth._authenticateLdap", e)
    return "error: internal server error"
  finally:
    if l: l.unbind()

def _authenticateLocal (username, password):
  u = _users.get(username, None)
  if u and password == u[0]:
    return AuthenticatedUser((username, u[1]), (u[2], u[3]))
  else:
    return None

def authenticate (username, password):
  """
  Authenticates a username and password.  Returns an AuthenticatedUser
  object (defined in this module) if the authentication was
  successful, None if unsuccessful, or a string message if an error
  occurred.
  """
  username = username.strip()
  if username == "": return "error: bad request - username required"
  password = password.strip()
  if _ldapEnabled:
    return _authenticateLdap(username, password)
  else:
    return _authenticateLocal(username, password)

def authenticateRequest (request):
  """
  Authenticates a Django request.  Returns an AuthenticatedUser object
  (defined in this module) if the authentication was successful, None
  if unsuccessful, or a string message if an error occurred.
  """
  if "auth" in request.session:
    return request.session["auth"]
  elif "HTTP_AUTHORIZATION" in request.META:
    if django.conf.settings.SSL and not request.is_secure():
      return "error: bad request - credentials sent over insecure channel"
    h = request.META["HTTP_AUTHORIZATION"].split()
    if len(h) != 2 or h[0] != "Basic": return None
    try:
      s = base64.decodestring(h[1])
    except:
      return None
    if ":" not in s: return None
    r = authenticate(*s.split(":", 1))
    if type(r) is AuthenticatedUser: request.session["auth"] = r
    return r
  else:
    return None

def clearLdapCache (username):
  """
  Clears the LDAP cache for a username.
  """
  _lock.acquire()
  try:
    if username in _ldapCache: del _ldapCache[username]
  finally:
    _lock.release()
