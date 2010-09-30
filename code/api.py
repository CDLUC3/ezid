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
# Login to obtain session cookie, nothing else:
#   GET /ezid/login   [authentication required]
#   response body: status line
#
# Logout:
#   GET /ezid/logout
#   response body: status line
#
# Get EZID's status:
#   GET /ezid/status
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
import urllib

import anvl
import config
import ezid
import userauth

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

def _response (content, createRequest=False, addAuthenticateHeader=False):
  c = content.encode("UTF-8")
  r = django.http.HttpResponse(c,
    status=_statusMapping(content, createRequest),
    content_type="text/plain; charset=UTF-8")
  r["Content-Length"] = len(c)
  if addAuthenticateHeader: r["WWW-Authenticate"] = "Basic realm=\"EZID\""
  return r

def _unauthorized ():
  return _response("error: unauthorized", addAuthenticateHeader=True)

def _methodNotAllowed ():
  return _response("error: method not allowed\n" +\
    "  EZID API, Version 2.\n" +\
    "  Please report problems to ezid-l at ucop dot edu.\n" +\
    "  See http://www.cdlib.org/uc3/docs/ezidapi.html for usage instructions.")

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
  assert request.path.startswith("/ezid/shoulder/")
  prefix = urllib.unquote(request.path[15:])
  s = ezid.mintIdentifier(prefix, auth.user, auth.group, target)
  if not s.startswith("success:"): return _response(s)
  if len(metadata) > 0:
    identifier = s[8:].strip()
    s = ezid.setMetadata(identifier, auth.user, auth.group, metadata)
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
  else:
    return _methodNotAllowed()

def _getMetadata (request):
  assert request.path.startswith("/ezid/id/")
  r = ezid.getMetadata(urllib.unquote(request.path[9:]))
  if type(r) is str: return _response(r)
  s, metadata = r
  return _response("%s\n%s" % (s, anvl.format(metadata)))

def _setMetadata (request):
  auth = userauth.authenticateRequest(request)
  if type(auth) is str:
    return _response(auth)
  elif not auth:
    return _unauthorized()
  metadata = _readInput(request)
  if type(metadata) is str: return _response(metadata)
  assert request.path.startswith("/ezid/id/")
  identifier = urllib.unquote(request.path[9:])
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
  assert request.path.startswith("/ezid/id/")
  identifier = urllib.unquote(request.path[9:])
  s = ezid.createIdentifier(identifier, auth.user, auth.group, target)
  if not s.startswith("success:"): return _response(s)
  if len(metadata) > 0:
    s = ezid.setMetadata(identifier, auth.user, auth.group, metadata)
  return _response(s, createRequest=True)

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
  nl = ezid.numIdentifiersLocked()
  s = "" if nl == 1 else "s"
  return _response("success: %d identifier%s currently locked" % (nl, s))

def reload (request):
  """
  Reloads the configuration file; interface to config.load.
  """
  if request.method != "POST": return _methodNotAllowed()
  auth = userauth.authenticateRequest(request)
  if type(auth) is str:
    return _response(auth)
  elif not auth or auth.user[0] != "admin":
    return _unauthorized()
  config.load()
  return _response("success: configuration file reloaded and caches emptied")
