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
import hashlib
import ldap
import ldap.dn
import threading
import time

import config
import log
import util

_ldapEnabled = None
_ldapServer = None
_numAttempts = None
_reattemptDelay = None
_lock = threading.Lock()
_ldapCache = None # { username: (hashed password or None, time,
                  #   AuthenticatedUser), ... }
_userDnTemplate = None
_adminUsername = None
_adminPassword = None
_users = None
_cachedPasswordLifetime = None

def _loadConfig ():
  global _ldapEnabled, _ldapServer, _numAttempts, _reattemptDelay, _ldapCache
  global _userDnTemplate, _adminUsername, _adminPassword, _users
  global _cachedPasswordLifetime
  _ldapEnabled = (config.config("ldap.enabled").lower() == "true")
  _ldapServer = config.config("ldap.server")
  _numAttempts = int(config.config("ldap.num_attempts"))
  _reattemptDelay = float(config.config("ldap.reattempt_delay"))
  _lock.acquire()
  _ldapCache = {}
  _lock.release()
  _userDnTemplate = config.config("ldap.user_dn_template")
  _adminUsername = config.config("ldap.admin_username")
  _adminPassword = config.config("ldap.admin_password")
  groupIds = dict([k, config.config("group_%s.id" % k)]\
    for k in config.config("groups.keys").split(","))
  _users = dict([k, (config.config("user_%s.password" % k),
    config.config("user_%s.id" % k), config.config("user_%s.group" % k),
    groupIds[config.config("user_%s.group" % k)])]\
    for k in config.config("users.keys").split(","))
  _cachedPasswordLifetime = int(config.config("ldap.cached_password_lifetime"))

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

def _authenticateLdap (username, password, authenticateAsAdmin=False):
  # Authenticate against a cached password, if one exists and it
  # hasn't expired.
  if not authenticateAsAdmin:
    _lock.acquire()
    try:
      if username in _ldapCache:
        hp, t, au = _ldapCache[username]
        if hp != None and int(time.time()) < t+_cachedPasswordLifetime:
          if hashlib.sha1(password).digest() == hp:
            return au
          else:
            return None
    finally:
      _lock.release()
  # Looks like we have to authenticate against LDAP.
  l = None
  try:
    if authenticateAsAdmin:
      userDn = _userDnTemplate % ldap.dn.escape_dn_chars(_adminUsername)
    else:
      userDn = _userDnTemplate % ldap.dn.escape_dn_chars(username)
    # We don't do retries on every LDAP interaction, but the following
    # 'bind' is the most frequently executed LDAP call, and the most
    # likely place in EZID where a down/inaccessible LDAP server will
    # be encountered and can easily be recovered from.
    for i in range(_numAttempts):
      # On network error the LDAP object gets boogered, so it must be
      # re-created on each attempt.
      l = ldap.initialize(_ldapServer)
      try:
        l.bind_s(userDn, password, ldap.AUTH_SIMPLE)
      except ldap.INVALID_CREDENTIALS:
        return None
      except ldap.UNWILLING_TO_PERFORM:
        # E.g., server won't accept empty password.
        return None
      except ldap.SERVER_DOWN:
        if i == _numAttempts-1:
          raise
        else:
          time.sleep(_reattemptDelay)
      else:
        break
    # Authentication successful.  Return a cached AuthenticatedUser
    # object, if there is one, and if so, update the cached password.
    _lock.acquire()
    try:
      if username in _ldapCache:
        hp, t, au = _ldapCache[username]
        if not authenticateAsAdmin:
          _ldapCache[username] = (hashlib.sha1(password).digest(),
            int(time.time()), au)
        return au
    finally:
      _lock.release()
    # Nothing in the cache, so LDAP must be queried to build an
    # AuthenticatedUser object.
    if authenticateAsAdmin:
      userDn = _userDnTemplate % ldap.dn.escape_dn_chars(username)
    try:
      ua = _getAttributes(l, userDn)
    except ldap.NO_SUCH_OBJECT:
      if authenticateAsAdmin:
        return None
      else:
        raise
    # Sanity checks.
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
    # Cache the password and AuthenticatedUser object.
    _lock.acquire()
    try:
      if authenticateAsAdmin:
        _ldapCache[username] = (None, None, au)
      else:
        _ldapCache[username] = (hashlib.sha1(password).digest(),
          int(time.time()), au)
    finally:
      _lock.release()
    return au
  except Exception, e:
    log.otherError("userauth._authenticateLdap", e)
    return "error: internal server error"
  finally:
    if l: l.unbind()

def _authenticateLocal (username, password, bypass=False):
  u = _users.get(username, None)
  if u and (bypass or password == u[0]):
    return AuthenticatedUser((username, u[1]), (u[2], u[3]))
  else:
    return None

def authenticate (username, password):
  """
  Authenticates a username and password.  Returns an AuthenticatedUser
  object (defined in this module) if the authentication was
  successful, None if unsuccessful, or a string message if an error
  occurred.  Easter egg: if the username has the form "@user" and the
  EZID administrator password is given, and if username "user" exists,
  then an AuthenticatedUser object for "user" is returned.
  """
  if username.startswith("@"):
    username = username[1:]
    sudo =  True
  else:
    sudo = False
  username = username.strip()
  if username == "": return "error: bad request - username required"
  password = password.strip()
  if _ldapEnabled:
    return _authenticateLdap(username, password, authenticateAsAdmin=sudo)
  else:
    if sudo:
      if _authenticateLocal(_adminUsername, password) != None:
        return _authenticateLocal(username, None, bypass=True)
      else:
        None
    else:
      return _authenticateLocal(username, password)

def authenticateRequest (request, storeSessionCookie=False):
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
    if type(r) is AuthenticatedUser and storeSessionCookie:
      request.session["auth"] = r
    return r
  else:
    return None

def getAuthenticatedUser (username):
  """
  Returns an AuthenticatedUser object for a username.  Throws an
  exception on error.  The need for this function will go away when
  EZID has a proper user model.
  """
  if _ldapEnabled:
    _lock.acquire()
    try:
      if username in _ldapCache: return _ldapCache[username][2]
    finally:
      _lock.release()
    au = _authenticateLdap(username, _adminPassword, authenticateAsAdmin=True)
    assert type(au) is AuthenticatedUser, "user lookup failed"
  else:
    au = _authenticateLocal(username, None, bypass=True)
    assert au is not None, "username not found"
  return au

def clearLdapCache (username):
  """
  Clears the LDAP cache for a username.
  """
  _lock.acquire()
  try:
    if username in _ldapCache: del _ldapCache[username]
  finally:
    _lock.release()
