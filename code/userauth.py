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
import django.contrib.auth
import django.contrib.auth.hashers
import django.contrib.auth.models
import django.utils.encoding
import hashlib

import ezidapp.models
import log

SESSION_KEY = "ezidAuthenticatedUser"

def authenticate (username, password, request=None, coAuthenticate=True):
  """
  Authenticates a username and password.  Returns a StoreUser object
  if the authentication is successful, None if unsuccessful, or a
  string error message if an error occurs.  If 'request' is not None,
  the appropriate variables are added to the request session.  If
  'request' is not None and coAuthenticate is True, and if the user is
  an administrative user, the user is authenticated with the Django
  admin app as well.  Easter egg: if the username has the form "@user"
  and the EZID administrator password is given, and if username "user"
  exists, then a StoreUser object for "user" is returned (even if
  logins are not enabled for the user).
  """
  if username.startswith("@"):
    username = username[1:]
    sudo =  True
  else:
    sudo = False
  username = username.strip()
  if username == "": return "error: bad request - username required"
  password = password.strip()
  if password == "": return "error: bad request - password required"
  user = ezidapp.models.getUserByUsername(username)
  if user == None or user.isAnonymous: return None
  if (sudo and ezidapp.models.getAdminUser().authenticate(password)) or\
    (not sudo and user.authenticate(password)):
    if request != None:
      request.session[SESSION_KEY] = user.id
      # Add session variables to support the Django admin interface.
      if coAuthenticate and not sudo and\
        django.contrib.auth.models.User.objects.filter(username=username)\
        .exists():
        authUser = django.contrib.auth.authenticate(username=username,
          password=password)
        if authUser != None:
          django.contrib.auth.login(request, authUser)
        else:
          log.otherError("userauth.authenticate", Exception(
            "administrator password mismatch; run " +\
            "'django-admin ezidadminsetpassword' to correct"))
    return user
  else:
    return None

def getUser (request, returnAnonymous=False):
  """
  If the session is authenticated, returns a StoreUser object for the
  authenticated user; otherwise, returns None.  If returnAnonymous is
  True, AnonymousUser is returned instead of None.
  """
  if SESSION_KEY in request.session:
    user = ezidapp.models.getUserById(request.session[SESSION_KEY])
    if user != None and user.loginEnabled:
      return user
    else:
      return ezidapp.models.AnonymousUser if returnAnonymous else None
  else:
    return ezidapp.models.AnonymousUser if returnAnonymous else None

def authenticateRequest (request, storeSessionCookie=False):
  """
  Authenticates an API request.  Returns a StoreUser object if the
  authentication is successful, None if unsuccessful, or a string
  error message if an error occurs.
  """
  if SESSION_KEY in request.session:
    user = ezidapp.models.getUserById(request.session[SESSION_KEY])
    if user != None and user.loginEnabled:
      return user
    else:
      return None
  elif "HTTP_AUTHORIZATION" in request.META:
    if django.conf.settings.USE_SSL and not request.is_secure():
      return "error: bad request - credentials sent over insecure channel"
    h = request.META["HTTP_AUTHORIZATION"].split()
    try:
      assert len(h) == 2 and h[0] == "Basic"
      s = base64.decodestring(h[1])
      assert ":" in s
    except:
      return "error: bad request - malformed Authorization header"
    return authenticate(*s.split(":", 1),
      request=(request if storeSessionCookie else None), coAuthenticate=False)
  else:
    return None

class LdapSha1PasswordHasher (django.contrib.auth.hashers.SHA1PasswordHasher):
  # Password hasher for legacy LDAP-encoded passwords.  File this
  # under So Close, Yet So Far.  LDAP uses salted SHA-1 hashing, and
  # Django supports exactly that scheme.  With some syntactic
  # shuffling it would be possible for Django to work with
  # LDAP-encoded passwords directly, except: LDAP uses binary salts,
  # whereas Django requires salts to be text.  Ergo, this custom
  # hasher.
  algorithm = "ldap_sha1"
  def encode (self, password, salt):
    assert password is not None
    assert len(salt) == 16
    binarySalt = "".join(chr(int(salt[i:i+2], 16)) for i in range(0, 16, 2))
    hash = hashlib.sha1(django.utils.encoding.force_bytes(password) +\
      binarySalt).hexdigest()
    return "%s$%s$%s" % (self.algorithm, salt, hash)
  def convertLegacyRepresentation (self, legacy):
    # Converts a legacy LDAP-encoded password to Django syntax.  In
    # LDAP encoding, a 20-byte binary SHA-1 hash and an 8-byte binary
    # salt are concatenated, Base64-encoded, and prepended with
    # "{SSHA}".
    assert legacy.startswith("{SSHA}")
    d = base64.b64decode(legacy[6:])
    assert len(d) == 28
    hash = d[:20]
    salt = d[20:]
    def hexify (s):
      return "".join("%02x" % ord(c) for c in s)
    return "%s$%s$%s" % (self.algorithm, hexify(salt), hexify(hash))
