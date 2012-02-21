# =============================================================================
#
# EZID :: api.py
#
# RESTful API to EZID services.  In the methods listed below, both
# request bodies and response bodies have content type text/plain and
# are formatted as ANVL.  Response character encoding is always UTF-8;
# request character encoding must be UTF-8, and if not stated, is
# assumed to be UTF-8.  See anvl.parse and anvl.format for additional
# percent-encoding.  In responses, the first line is always a status
# line.  For those methods requiring authentication, credentials may
# be supplied using HTTP Basic authentication; thereafter, session
# cookies may be used.  Methods provided:
#
# Mint an identifier:
#   POST /ezid/shoulder/{prefix}   [authentication required]
#   request body: optional metadata
#   response body: status line
#
# Create an identifier:
#   PUT /ezid/id/{identifier}   [authentication required]
#   request body: optional metadata
#   response body: status line
#
# View an identifier:
#   GET /ezid/id/{identifier}
#   response body: status line, metadata
#
# Update an identifier:
#   POST /ezid/id/{identifier}   [authentication required]
#   request body: optional metadata
#   response body: status line
#
# Delete an identifier:
#   DELETE /ezid/id/{identifier}   [authentication required]
#   response body: status line
#
# Login to obtain session cookie, nothing else:
#   GET /ezid/login   [authentication required]
#   response body: status line
#
# Logout:
#   GET /ezid/logout
#   response body: status line
#
# Get EZID's status:
#   GET /ezid/status?subsystems={*|subsystemlist}
#   response body: status line
#
# Reload configuration file and clear caches:
#   POST /ezid/admin/reload   [admin authentication required]
#   request body: empty
#   response body: status line
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2010, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.http

import anvl
import config
import datacite
import ezid
import ezidadmin
import noid
import userauth

_adminUsername = None
_bindNoid = None

def _loadConfig ():
  global _adminUsername, _bindNoid
  _adminUsername = config.config("ldap.admin_username")
  _bindNoid = noid.Noid(config.config("DEFAULT.bind_noid"))

_loadConfig()
config.addLoader(_loadConfig)

def _readInput (request):
  if "CONTENT_TYPE" in request.META:
    ct = [w.strip() for w in request.META["CONTENT_TYPE"].split(";")]
    if ct[0] != "text/plain":
      return "error: bad request - unsupported content type"
    if len(ct) > 1 and ct[1].startswith("charset=") and\
      ct[1][8:].upper() != "UTF-8":
      return "error: bad request - unsupported character encoding"
    try:
      return anvl.parse(request.raw_post_data.decode("UTF-8"))
    except anvl.AnvlParseException:
      return "error: bad request - ANVL parse error"
    except Exception:
      return "error: bad request - character decode error"
  else:
    return {}

def _statusMapping (content, createRequest):
  if content.startswith("success:"):
    return 201 if createRequest else 200
  elif content.startswith("error: bad request"):
    return 400
  elif content.startswith("error: unauthorized"):
    return 401
  elif content.startswith("error: method not allowed"):
    return 405
  else:
    return 500

def _response (status, createRequest=False, addAuthenticateHeader=False,
  anvlBody=""):
  c = anvl.formatPair(*[v.strip() for v in status.split(":", 1)])
  if len(anvlBody) > 0:
    c += anvlBody
  else:
    c = c[:-1]
  c = c.encode("UTF-8")
  r = django.http.HttpResponse(c, status=_statusMapping(status, createRequest),
    content_type="text/plain; charset=UTF-8")
  r["Content-Length"] = len(c)
  if addAuthenticateHeader: r["WWW-Authenticate"] = "Basic realm=\"EZID\""
  return r

def _unauthorized (authenticationFailure=True):
  if authenticationFailure:
    s = " - authentication failure"
  else:
    s = ""
  return _response("error: unauthorized" + s, addAuthenticateHeader=True)

def _methodNotAllowed ():
  return _response("error: method not allowed")

def mintIdentifier (request):
  """
  Mints an identifier; interface to ezid.mintIdentifier.
  """
  if request.method != "POST": return _methodNotAllowed()
  auth = userauth.authenticateRequest(request)
  if type(auth) is str:
    return _response(auth)
  elif not auth:
    return _unauthorized()
  metadata = _readInput(request)
  if type(metadata) is str: return _response(metadata)
  target = None
  if "_target" in metadata:
    target = metadata["_target"]
    del metadata["_target"]
  reserveOnly = False
  if "_status" in metadata and metadata["_status"] == "reserved":
    reserveOnly = True
    del metadata["_status"]
  assert request.path.startswith("/ezid/shoulder/")
  prefix = request.path[15:]
  s = ezid.mintIdentifier(prefix, auth.user, auth.group, target, reserveOnly)
  if not s.startswith("success:"): return _response(s)
  if len(metadata) > 0:
    identifier = s.split()[1]
    s2 = ezid.setMetadata(identifier, auth.user, auth.group, metadata)
    if not s2.startswith("success:"): s = s2
  return _response(s, createRequest=True)

def identifierDispatcher (request):
  """
  Dispatches an identifier request depending on the HTTP method;
  interface to ezid.getMetadata, ezid.setMetadata, and
  ezid.createIdentifier.
  """
  if request.method == "GET":
    return _getMetadata(request)
  elif request.method == "POST":
    return _setMetadata(request)
  elif request.method == "PUT":
    return _createIdentifier(request)
  elif request.method == "DELETE":
    return _deleteIdentifier(request)
  else:
    return _methodNotAllowed()

def _getMetadata (request):
  assert request.path.startswith("/ezid/id/")
  r = ezid.getMetadata(request.path[9:])
  if type(r) is str: return _response(r)
  s, metadata = r
  if "_ezid_role" in metadata:
    # Special case.
    auth = userauth.authenticateRequest(request)
    if type(auth) is str:
      return _response(auth)
    elif not auth:
      return _unauthorized()
    elif auth.user[0] != _adminUsername:
      return _unauthorized(False)
  return _response(s, anvlBody=anvl.format(metadata))

def _setMetadata (request):
  auth = userauth.authenticateRequest(request)
  if type(auth) is str:
    return _response(auth)
  elif not auth:
    return _unauthorized()
  metadata = _readInput(request)
  if type(metadata) is str: return _response(metadata)
  assert request.path.startswith("/ezid/id/")
  identifier = request.path[9:]
  return _response(ezid.setMetadata(identifier, auth.user, auth.group,
    metadata))

def _createIdentifier (request):
  auth = userauth.authenticateRequest(request)
  if type(auth) is str:
    return _response(auth)
  elif not auth:
    return _unauthorized()
  metadata = _readInput(request)
  if type(metadata) is str: return _response(metadata)
  target = None
  if "_target" in metadata:
    target = metadata["_target"]
    del metadata["_target"]
  reserveOnly = False
  if "_status" in metadata and metadata["_status"] == "reserved":
    reserveOnly = True
    del metadata["_status"]
  assert request.path.startswith("/ezid/id/")
  identifier = request.path[9:]
  s = ezid.createIdentifier(identifier, auth.user, auth.group, target,
    reserveOnly)
  if not s.startswith("success:"): return _response(s)
  if len(metadata) > 0:
    identifier = s.split()[1]
    s2 = ezid.setMetadata(identifier, auth.user, auth.group, metadata)
    if not s2.startswith("success:"): s = s2
  return _response(s, createRequest=True)

def _deleteIdentifier (request):
  auth = userauth.authenticateRequest(request)
  if type(auth) is str:
    return _response(auth)
  elif not auth:
    return _unauthorized()
  assert request.path.startswith("/ezid/id/")
  identifier = request.path[9:]
  return _response(ezid.deleteIdentifier(identifier, auth.user, auth.group))

def login (request):
  """
  Logs in a user.
  """
  if request.method != "GET": return _methodNotAllowed()
  auth = userauth.authenticateRequest(request)
  if type(auth) is str:
    return _response(auth)
  elif not auth:
    return _unauthorized()
  else:
    return _response("success: session cookie returned")

def logout (request):
  """
  Logs a user out.
  """
  if request.method != "GET": return _methodNotAllowed()
  request.session.flush()
  return _response("success: authentication credentials flushed")

def getStatus (request):
  """
  Returns EZID's status.
  """
  if request.method != "GET": return _methodNotAllowed()
  body = ""
  if "subsystems" in request.GET:
    l = request.GET["subsystems"]
    if l == "*": l = "datacite,ldap,noid"
    for ss in [ss.strip() for ss in l.split(",") if len(ss.strip()) > 0]:
      if ss == "datacite":
        body += "datacite: %s\n" % datacite.ping()
      elif ss == "ldap":
        body += "ldap: %s\n" % ezidadmin.pingLdap()
      elif ss == "noid":
        body += "noid: %s\n" % _bindNoid.ping()
      else:
        return _response("error: bad request - no such subsystem")
  nl = ezid.numIdentifiersLocked()
  s = "" if nl == 1 else "s"
  return _response("success: %d identifier%s currently locked" % (nl, s),
    anvlBody=body)

def reload (request):
  """
  Reloads the configuration file; interface to config.load.
  """
  if request.method != "POST": return _methodNotAllowed()
  auth = userauth.authenticateRequest(request)
  if type(auth) is str:
    return _response(auth)
  elif not auth:
    return _unauthorized()
  elif auth.user[0] != _adminUsername:
    return _unauthorized(False)
  config.load()
  return _response("success: configuration file reloaded and caches emptied")
