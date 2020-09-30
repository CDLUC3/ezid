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
#   POST /shoulder/{shoulder}   [authentication required]
#   request body: optional metadata
#   response body: status line
#
# Create an identifier:
#   PUT /id/{identifier}   [authentication required]
#     ?update_if_exists={yes|no}
#   request body: optional metadata
#   response body: status line
#
# View an identifier:
#   GET /id/{identifier}   [authentication optional]
#     ?prefix_match={yes|no}
#   response body: status line, metadata
#
# Update an identifier:
#   POST /id/{identifier}   [authentication required]
#     ?update_external_services={yes|no}
#   request body: optional metadata
#   response body: status line
#
# Delete an identifier:
#   DELETE /id/{identifier}   [authentication required]
#     ?update_external_services={yes|no}
#   response body: status line
#
# Login to obtain session cookie, nothing else:
#   GET /login   [authentication required]
#   response body: status line
#
# Logout:
#   GET /logout
#   response body: status line
#
# Get EZID's status:
#   GET /status
#     ?detailed={yes|no}
#     ?subsystems={*|subsystemlist}
#   response body: status line, optional additional status information
#
# Get EZID's version:
#   GET /version
#   response body: status line, version information
#
# Pause the server:
#   GET /admin/pause?op={on|off|idlewait|monitor}   [admin auth required]
#   request body: empty
#   response body: status line followed by, for op=on and op=monitor,
#     server status records streamed back indefinitely
#
# Reload configuration file and clear caches:
#   POST /admin/reload   [admin authentication required]
#   request body: empty
#   response body: status line
#
# Request a batch download:
#   POST /download_request   [authentication required]
#   request body: application/x-www-form-urlencoded
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

import time

import django.http

import anvl
import binder_async
import config
import datacite
import datacite_async
import download
import ezid
import ezidapp.models
import noid_egg
import search_util
import userauth
import util


def _readInput(request):
    if "CONTENT_TYPE" in request.META:
        ct = [w.strip() for w in request.META["CONTENT_TYPE"].split(";")]
        if ct[0] != "text/plain":
            return "error: bad request - unsupported content type"
        if (
            len(ct) > 1
            and ct[1].startswith("charset=")
            and ct[1][8:].upper() != "UTF-8"
        ):
            return "error: bad request - unsupported character encoding"
        try:
            # We'd like to call sanitizeXmlSafeCharset just once, before the
            # ANVL parsing, but the problem is that hex-percent-encoded
            # characters, when decoded, can result in additional disallowed
            # characters appearing.  So we sanitize after ANVL parsing.
            # Note that it is possible here that two different labels, that
            # differ in only disallowed characters, will be silently
            # collapsed into one instead of resulting in an error.  But
            # that's a real edge case, so we don't worry about it.
            return {
                util.sanitizeXmlSafeCharset(k): util.sanitizeXmlSafeCharset(v)
                for k, v in anvl.parse(request.body.decode("UTF-8")).items()
            }
        except UnicodeDecodeError:
            return "error: bad request - character decoding error"
        except anvl.AnvlParseException, e:
            return "error: bad request - ANVL parse error (%s)" % str(e)
        except:
            return "error: bad request - malformed or incomplete request body"
    else:
        return {}


def _validateOptions(request, options):
    d = {}
    for k, v in request.GET.items():
        if k in options:
            if options[k] == None:
                d[k] = v
            else:
                found = False
                for ov in options[k]:
                    if (type(ov) is tuple and v.lower() == ov[0]) or (
                        type(ov) is str and v.lower() == ov
                    ):
                        d[k] = ov[1] if type(ov) is tuple else ov
                        found = True
                        break
                if not found:
                    return (
                        "error: bad request - "
                        + "invalid value for URL query parameter '%s'"
                    ) % k.encode("ASCII", "xmlcharrefreplace")
        else:
            return (
                "error: bad request - unrecognized URL query parameter '%s'"
                % util.oneLine(k.encode("ASCII", "xmlcharrefreplace"))
            )
    return d


def _statusMapping(content, createRequest):
    if content.startswith("success:"):
        return 201 if createRequest else 200
    elif content.startswith("error: bad request"):
        return 400
    elif content.startswith("error: unauthorized"):
        return 401
    elif content.startswith("error: forbidden"):
        return 403
    elif content.startswith("error: method not allowed"):
        return 405
    elif content.startswith("error: concurrency limit exceeded"):
        return 503
    else:
        return 500


def _response(status, createRequest=False, addAuthenticateHeader=False, anvlBody=""):
    c = anvl.formatPair(*[v.strip() for v in status.split(":", 1)])
    if len(anvlBody) > 0:
        c += anvlBody
    else:
        c = c[:-1]
    c = c.encode("UTF-8")
    r = django.http.HttpResponse(
        c,
        status=_statusMapping(status, createRequest),
        content_type="text/plain; charset=UTF-8",
    )
    r["Content-Length"] = len(c)
    if addAuthenticateHeader:
        r["WWW-Authenticate"] = "Basic realm=\"EZID\""
    return r


def _unauthorized():
    return _response("error: unauthorized", addAuthenticateHeader=True)


def _forbidden():
    return _response("error: forbidden")


def _methodNotAllowed():
    return _response("error: method not allowed")


def mintIdentifier(request):
    """
  Mints an identifier; interface to ezid.mintIdentifier.
  """
    if request.method != "POST":
        return _methodNotAllowed()
    user = userauth.authenticateRequest(request)
    if type(user) is str:
        return _response(user)
    elif not user:
        return _unauthorized()
    metadata = _readInput(request)
    if type(metadata) is str:
        return _response(metadata)
    options = _validateOptions(request, {})
    if type(options) is str:
        return _response(options)
    assert request.path_info.startswith("/shoulder/")
    shoulder = request.path_info[10:]
    return _response(ezid.mintIdentifier(shoulder, user, metadata), createRequest=True)


def identifierDispatcher(request):
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


def _getMetadata(request):
    assert request.path_info.startswith("/id/")
    user = userauth.authenticateRequest(request)
    if type(user) is str:
        return _response(user)
    options = _validateOptions(
        request, {"prefix_match": [("yes", True), ("no", False)]}
    )
    if type(options) is str:
        return _response(options)
    if user != None:
        r = ezid.getMetadata(
            request.path_info[4:], user, prefixMatch=options.get("prefix_match", False)
        )
    else:
        r = ezid.getMetadata(
            request.path_info[4:], prefixMatch=options.get("prefix_match", False)
        )
    if type(r) is str:
        if r.startswith("error: forbidden"):
            if user != None:
                return _forbidden()
            else:
                return _unauthorized()
        else:
            return _response(r)
    s, metadata = r
    return _response(s, anvlBody=anvl.format(metadata))


def _setMetadata(request):
    user = userauth.authenticateRequest(request)
    if type(user) is str:
        return _response(user)
    elif user == None:
        return _unauthorized()
    metadata = _readInput(request)
    if type(metadata) is str:
        return _response(metadata)
    # Easter egg.
    options = _validateOptions(
        request,
        {"update_external_services": [("yes", True), ("no", False)]}
        if user.isSuperuser
        else {},
    )
    if type(options) is str:
        return _response(options)
    assert request.path_info.startswith("/id/")
    identifier = request.path_info[4:]
    return _response(
        ezid.setMetadata(
            identifier,
            user,
            metadata,
            updateExternalServices=options.get("update_external_services", True),
        )
    )


def _createIdentifier(request):
    user = userauth.authenticateRequest(request)
    if type(user) is str:
        return _response(user)
    elif not user:
        return _unauthorized()
    metadata = _readInput(request)
    if type(metadata) is str:
        return _response(metadata)
    options = _validateOptions(
        request, {"update_if_exists": [("yes", True), ("no", False)]}
    )
    if type(options) is str:
        return _response(options)
    assert request.path_info.startswith("/id/")
    identifier = request.path_info[4:]
    return _response(
        ezid.createIdentifier(
            identifier,
            user,
            metadata,
            updateIfExists=options.get("update_if_exists", False),
        ),
        createRequest=True,
    )


def _deleteIdentifier(request):
    user = userauth.authenticateRequest(request)
    if type(user) is str:
        return _response(user)
    elif not user:
        return _unauthorized()
    # Easter egg.
    options = _validateOptions(
        request,
        {"update_external_services": [("yes", True), ("no", False)]}
        if user.isSuperuser
        else {},
    )
    if type(options) is str:
        return _response(options)
    assert request.path_info.startswith("/id/")
    identifier = request.path_info[4:]
    return _response(
        ezid.deleteIdentifier(
            identifier,
            user,
            updateExternalServices=options.get("update_external_services", True),
        )
    )


def login(request):
    """
  Logs in a user.
  """
    if request.method != "GET":
        return _methodNotAllowed()
    options = _validateOptions(request, {})
    if type(options) is str:
        return _response(options)
    user = userauth.authenticateRequest(request, storeSessionCookie=True)
    if type(user) is str:
        return _response(user)
    elif user == None:
        return _unauthorized()
    else:
        return _response("success: session cookie returned")


def logout(request):
    """
  Logs a user out.
  """
    if request.method != "GET":
        return _methodNotAllowed()
    options = _validateOptions(request, {})
    if type(options) is str:
        return _response(options)
    request.session.flush()
    return _response("success: authentication credentials flushed")


def getStatus(request):
    """
  Returns EZID's status.
  """
    if request.method != "GET":
        return _methodNotAllowed()
    options = _validateOptions(
        request, {"subsystems": None, "detailed": [("yes", True), ("no", False)]}
    )
    if type(options) is str:
        return _response(options)
    if options.get("detailed", False):
        statusLine = _statusLineGenerator(False).next()[7:]
    else:
        statusLine = "EZID is up"
    body = ""
    if "subsystems" in options:
        l = options["subsystems"]
        if l == "*":
            l = "binder,datacite,search"
        for ss in [ss.strip() for ss in l.split(",") if len(ss.strip()) > 0]:
            if ss == "binder":
                body += "binder: %s\n" % noid_egg.ping()
            elif ss == "datacite":
                body += "datacite: %s\n" % datacite.ping()
            elif ss == "search":
                body += "search: %s\n" % search_util.ping()
            else:
                return _response("error: bad request - no such subsystem")
    return _response("success: " + statusLine, anvlBody=body)


def getVersion(request):
    """
    Returns EZID's version.
    """
    if request.method != "GET":
        return _methodNotAllowed()

    # TODO: This is currently disabled as it relies on Mercurial.
    return django.http.HttpResponse(
        'version currently not available',
        content_type="text/plain; charset=UTF-8",
    )

    options = _validateOptions(request, {})
    if type(options) is str:
        return _response(options)
    sv, v = config.getVersionInfo()
    # In theory the following body should be encoded, but no percent
    # signs should appear anywhere.
    body = (
        "startup.time: %s\n"
        + "startup.ezid_version: %s\n"
        + "startup.info_version: %s\n"
        + "last_reload.time: %s\n"
        + "last_reload.ezid_version: %s\n"
        + "last_reload.info_version: %s\n"
    ) % (
        time.asctime(time.localtime(sv[0])),
        sv[1],
        sv[2],
        time.asctime(time.localtime(v[0])),
        v[1],
        v[2],
    )
    return _response("success: version information follows", anvlBody=body)


def _formatUserCountList(d):
    if len(d) > 0:
        l = d.items()
        l.sort(cmp=lambda x, y: -cmp(x[1], y[1]))
        return " (" + " ".join("%s=%d" % i for i in l) + ")"
    else:
        return ""


def _statusLineGenerator(includeSuccessLine):
    if includeSuccessLine:
        yield "success: server paused\n"
    while True:
        activeUsers, waitingUsers, isPaused = ezid.getStatus()
        na = sum(activeUsers.values())
        nw = sum(waitingUsers.values())
        ndo = datacite.numActiveOperations()
        ql = ezidapp.models.UpdateQueue.objects.count()
        bql = binder_async.getQueueLength()
        dql = datacite_async.getQueueLength()
        nas = search_util.numActiveSearches()
        s = (
            "STATUS %s activeOperations=%d%s waitingRequests=%d%s "
            + "activeDataciteOperations=%d updateQueueLength=%d "
            + "binderQueueLength=%d "
            + "dataciteQueueLength=%d activeSearches=%d\n"
        ) % (
            "paused" if isPaused else "running",
            na,
            _formatUserCountList(activeUsers),
            nw,
            _formatUserCountList(waitingUsers),
            ndo,
            ql,
            bql,
            dql,
            nas,
        )
        yield s.encode("UTF-8")
        time.sleep(3)


def pause(request):
    """
  Pauses or unpauses the server.  If the server is paused, server
  status records are streamed back to the client indefinitely.
  """
    if request.method != "GET":
        return _methodNotAllowed()
    user = userauth.authenticateRequest(request)
    if type(user) is str:
        return _response(user)
    elif user == None:
        return _unauthorized()
    elif not user.isSuperuser:
        return _forbidden()
    options = _validateOptions(request, {"op": ["on", "idlewait", "off", "monitor"]})
    if type(options) is str:
        return _response(options)
    if "op" not in options:
        return _response("error: bad request - no 'op' parameter")
    if options["op"] == "on":
        ezid.pause(True)
        return django.http.StreamingHttpResponse(
            _statusLineGenerator(True), content_type="text/plain; charset=UTF-8"
        )
    elif options["op"] == "idlewait":
        ezid.pause(True)
        while True:
            activeUsers, waitingUsers, isPaused = ezid.getStatus()
            if len(activeUsers) == 0:
                break
            time.sleep(1)
        return _response("success: server paused and idle")
    elif options["op"] == "off":
        ezid.pause(False)
        return _response("success: server unpaused")
    elif options["op"] == "monitor":
        return django.http.StreamingHttpResponse(
            _statusLineGenerator(False), content_type="text/plain; charset=UTF-8"
        )
    else:
        assert False, "unhandled case"


def reload(request):
    """
  Reloads the configuration file; interface to config.reload.
  """
    if request.method != "POST":
        return _methodNotAllowed()
    options = _validateOptions(request, {})
    if type(options) is str:
        return _response(options)
    user = userauth.authenticateRequest(request)
    if type(user) is str:
        return _response(user)
    elif user == None:
        return _unauthorized()
    elif not user.isSuperuser:
        return _forbidden()
    try:
        oldValue = ezid.pause(True)
        # Wait for the system to become quiescent.
        while True:
            if len(ezid.getStatus()[0]) == 0:
                break
            time.sleep(1)
        config.reload()
    finally:
        ezid.pause(oldValue)
    return _response("success: configuration file reloaded and caches emptied")


def batchDownloadRequest(request):
    """
  Enqueues a batch download request.
  """
    if request.method != "POST":
        return _methodNotAllowed()
    options = _validateOptions(request, {})
    if type(options) is str:
        return _response(options)
    user = userauth.authenticateRequest(request)
    if type(user) is str:
        return _response(user)
    elif not user:
        return _unauthorized()
    return _response(download.enqueueRequest(user, request.POST))
