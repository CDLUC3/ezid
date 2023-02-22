#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""RESTful API to EZID services

In the methods listed below, both request bodies and response bodies have content type
text/plain and are formatted as ANVL. Response character encoding is always UTF-8;
request character encoding must be UTF-8, and if not stated, is assumed to be UTF-8.
See anvl.parse and anvl.format for additional percent-encoding. In responses, the first
line is always a status line. For those methods requiring authentication, credentials
may be supplied using HTTP Basic authentication; thereafter, session cookies may be
used. Methods provided:

Mint an identifier:
  POST /shoulder/{shoulder}   [authentication required]
  request body: optional metadata
  response body: status line

Create an identifier:
  PUT /id/{identifier}   [authentication required]
    ?update_if_exists={yes|no}
  request body: optional metadata
  response body: status line

View an identifier:
  GET /id/{identifier}   [authentication optional]
    ?prefix_match={yes|no}
  response body: status line, metadata

Update an identifier:
  POST /id/{identifier}   [authentication required]
    ?update_external_services={yes|no}
  request body: optional metadata
  response body: status line

Delete an identifier:
  DELETE /id/{identifier}   [authentication required]
    ?update_external_services={yes|no}
  response body: status line

Login to obtain session cookie, nothing else:
  GET /login   [authentication required]
  response body: status line

Logout:
  GET /logout
  response body: status line

Get EZID's status:
  GET /status
    ?detailed={yes|no}
    ?subsystems={*|subsystemlist}
  response body: status line, optional additional status information

Get EZID's version:
  GET /version
  response body: status line, version information

Pause the server:
  GET /admin/pause?op={on|off|idlewait|monitor}   [admin auth required]
  request body: empty
  response body: status line followed by, for op=on and op=monitor,
    server status records streamed back indefinitely

Reload configuration file and clear caches:
  POST /admin/reload   [admin authentication required]
  request body: empty
  response body: status line

Request a batch download:
  POST /download_request   [authentication required]
  request body: application/x-www-form-urlencoded
  response body: status line

Resolve an identifier:
  GET /{identifier}
  response status: 302
  response body: json document with target info

Identifier inflection (introspection):
  GET /{identifier}? or ??
  response body as for View an identifier
"""
import cgi
import datetime
import json
import logging
import sys
import time
import urllib.parse

import django.conf
import django.http

import ezidapp.models.identifier
import ezidapp.models.shoulder

import impl.anvl
import impl.datacite
import impl.download
import impl.ezid
import impl.noid_egg
import impl.resolver
import impl.search_util
import impl.statistics
import impl.userauth
import impl.util
import impl.http_accept_types

HTTP_DATE_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"


def _parseAccept(request):
    '''
    Parse request Accept header and return a list of types
    in order of preference
    '''
    # From django-rest-framework/negotiation
    header = request.META.get('HTTP_ACCEPT', '*/*')
    tokens = [token.strip() for token in header.split(',')]
    
    pass

def _readInput(request):
    if not is_text_plain_utf8(request):
        return (
            'error: bad request - If specified, Content-Type must be text/plain '
            'and encoding must be UTF-8'
        )
    try:
        # We'd like to call sanitizeXmlSafeCharset just once, before the ANVL parsing,
        # but the problem is that hex-percent-encoded characters, when decoded, can
        # result in additional disallowed characters appearing. So we sanitize after
        # ANVL parsing.
        #
        # It is possible here that two different labels, that differ in only disallowed
        # characters, will be silently collapsed into one instead of resulting in an
        # error. But that's a real edge case, so we don't worry about it.
        return {
            impl.util.sanitizeXmlSafeCharset(k): impl.util.sanitizeXmlSafeCharset(v)
            for k, v in list(impl.anvl.parse(request.body.decode("utf-8")).items())
        }
    except UnicodeDecodeError:
        return "error: bad request - character decoding error"
    except impl.anvl.AnvlParseException as e:
        return f"error: bad request - ANVL parse error ({str(e)})"
    except Exception:
        msg_str = "error: bad request - malformed or incomplete request body"
        logging.exception(msg_str)
        return msg_str


def is_text_plain_utf8(request):
    content_type = request.META.get('CONTENT_TYPE', '')
    mimetype, options = cgi.parse_header(content_type)
    if mimetype not in ('text/plain', ''):
        return False
    if options.get('charset', 'utf-8').lower() != 'utf-8':
        return False
    return True


def _validateOptions(request, options):
    '''
    Returns a dict of parameters or a string on error
    '''
    d = {}
    for k, v in list(request.GET.items()):
        if k in options:
            if options[k] is None:
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
                        "error: bad request - invalid value for URL query parameter "
                        "'%s'".format(k)
                    )
        else:
            return "error: bad request - unrecognized URL query parameter '%s'" % impl.util.oneLine(
                # has the effect of XML encoding non-ascii chars
                k.encode("ASCII", "xmlcharrefreplace").decode()
            )
    return d


STATUS_CODE_MAP = [
    ("success:", 200),
    ("error: bad request", 400),
    ("error: unable to parse", 400),
    ("error: unauthorized", 401),
    ("error: forbidden", 403),
    ("error: method not allowed", 405),
    ("error: concurrency limit exceeded", 503),
]


def _statusMapping(content, createRequest):
    '''
    Map a response string to a response status code.

    Known errors must match here otherwise a 500 status
    is reported, which in turn will trigger an alert email.
    '''
    for test, code in STATUS_CODE_MAP:
        if content.startswith(test):
            if code == 200 and createRequest:
                # per API docs, successful create returns 201
                return 201
            return code
    # Note that 500 errors trigger an email to the settings.MANAGERS targets
    return 500


def _response(status, createRequest=False, addAuthenticateHeader=False, anvlBody=""):
    c = impl.anvl.formatPair(*[v.strip() for v in status.split(":", 1)])
    if len(anvlBody) > 0:
        c += anvlBody
    else:
        c = c[:-1]
    c = c.encode("utf-8")
    r = django.http.HttpResponse(
        c,
        status=_statusMapping(status, createRequest),
        content_type="text/plain; charset=utf-8",
    )
    r["Content-Length"] = len(c)
    if addAuthenticateHeader:
        r["WWW-Authenticate"] = 'Basic realm="EZID"'
    return r


def _unauthorized():
    return _response("error: unauthorized", addAuthenticateHeader=True)


def _forbidden():
    return _response("error: forbidden")


def _methodNotAllowed():
    return _response("error: method not allowed")


def mintIdentifier(request):
    """Mint an identifier; interface to ezid.mintIdentifier"""
    if request.method != "POST":
        return _methodNotAllowed()
    user = impl.userauth.authenticateRequest(request)
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
    return _response(impl.ezid.mintIdentifier(shoulder, user, metadata), createRequest=True)


def identifierDispatcher(request):
    """Dispatch an identifier request depending on the HTTP method"""
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
    user = impl.userauth.authenticateRequest(request)
    if type(user) is str:
        return _response(user)
    options = _validateOptions(request, {"prefix_match": [("yes", True), ("no", False)]})
    if type(options) is str:
        return _response(options)
    if user is not None:
        r = impl.ezid.getMetadata(
            request.path_info[4:], user, prefixMatch=options.get("prefix_match", False)
        )
    else:
        r = impl.ezid.getMetadata(
            request.path_info[4:], prefixMatch=options.get("prefix_match", False)
        )
    if type(r) is str:
        if r.startswith("error: forbidden"):
            if user is not None:
                return _forbidden()
            else:
                return _unauthorized()
        else:
            return _response(r)
    s, metadata = r
    return _response(s, anvlBody=impl.anvl.format(metadata))


def _setMetadata(request):
    user = impl.userauth.authenticateRequest(request)
    if type(user) is str:
        return _response(user)
    elif user is None:
        return _unauthorized()
    metadata = _readInput(request)
    if type(metadata) is str:
        return _response(metadata)
    # Easter egg.
    options = _validateOptions(
        request,
        {"update_external_services": [("yes", True), ("no", False)]} if user.isSuperuser else {},
    )
    if type(options) is str:
        return _response(options)
    assert request.path_info.startswith("/id/")
    identifier = request.path_info[4:]
    return _response(
        impl.ezid.setMetadata(
            identifier,
            user,
            metadata,
            updateExternalServices=options.get("update_external_services", True),
        )
    )


def _createIdentifier(request):
    user = impl.userauth.authenticateRequest(request)
    if type(user) is str:
        return _response(user)
    elif not user:
        return _unauthorized()
    metadata = _readInput(request)
    if type(metadata) is str:
        return _response(metadata)
    options = _validateOptions(request, {"update_if_exists": [("yes", True), ("no", False)]})
    if type(options) is str:
        return _response(options)
    assert request.path_info.startswith("/id/")
    identifier = request.path_info[4:]
    return _response(
        impl.ezid.createIdentifier(
            identifier,
            user,
            metadata,
            updateIfExists=options.get("update_if_exists", False),
        ),
        createRequest=True,
    )


def _deleteIdentifier(request):
    user = impl.userauth.authenticateRequest(request)
    if type(user) is str:
        return _response(user)
    elif not user:
        return _unauthorized()
    # Easter egg.
    options = _validateOptions(
        request,
        {"update_external_services": [("yes", True), ("no", False)]} if user.isSuperuser else {},
    )
    if type(options) is str:
        return _response(options)
    assert request.path_info.startswith("/id/")
    identifier = request.path_info[4:]
    return _response(
        impl.ezid.deleteIdentifier(
            identifier,
            user,
            updateExternalServices=options.get("update_external_services", True),
        )
    )


def login(request):
    """Log in a user"""
    if request.method != "GET":
        return _methodNotAllowed()
    options = _validateOptions(request, {})
    if type(options) is str:
        return _response(options)
    user = impl.userauth.authenticateRequest(request, storeSessionCookie=True)
    if type(user) is str:
        return _response(user)
    elif user is None:
        return _unauthorized()
    else:
        return _response("success: session cookie returned")


def logout(request):
    """Log a user out"""
    if request.method != "GET":
        return _methodNotAllowed()
    options = _validateOptions(request, {})
    if type(options) is str:
        return _response(options)
    request.session.flush()
    return _response("success: authentication credentials flushed")


def getStatus(request):
    """Return EZID's status"""
    if request.method != "GET":
        return _methodNotAllowed()
    options = _validateOptions(
        request, {"subsystems": None, "detailed": [("yes", True), ("no", False)]}
    )
    if type(options) is str:
        return _response(options)
    if options.get("detailed", False):
        statusLine = next(_statusLineGenerator(False))[7:]
    else:
        statusLine = "EZID is up"
    body = ""
    if "subsystems" in options:
        l = options["subsystems"]
        if l == "*":
            l = "binder,datacite,search"
        for ss in [ss.strip() for ss in l.split(",") if len(ss.strip()) > 0]:
            if ss == "binder":
                body += f"binder: {impl.noid_egg.ping()}\n"
            elif ss == "datacite":
                body += f"datacite: {impl.datacite.ping()}\n"
            elif ss == "search":
                body += f"search: {impl.search_util.ping()}\n"
            else:
                return _response("error: bad request - no such subsystem")
    return _response("success: " + statusLine, anvlBody=body)


def getVersion(request):
    """Return EZID's version as a semantic versioning (SemVer) string"""
    if request.method != "GET":
        return _methodNotAllowed()
    return django.http.HttpResponse(
        django.conf.settings.EZID_VERSION,
        content_type="text/plain; charset=utf-8",
    )


def batchDownloadRequest(request):
    """Enqueue a batch download request"""
    if request.method != "POST":
        return _methodNotAllowed()
    options = _validateOptions(request, {})
    if type(options) is str:
        return _response(options)
    user = impl.userauth.authenticateRequest(request)
    if type(user) is str:
        return _response(user)
    elif not user:
        return _unauthorized()
    return _response(impl.download.enqueueRequest(user, request.POST))


def _formatUserCountList(d):
    if len(d) > 0:
        l = list(d.items())
        l.sort(key=lambda x: -x[1])
        return " (" + " ".join("%s=%d" % i for i in l) + ")"
    else:
        return ""


def _statusLineGenerator(includeSuccessLine):
    if includeSuccessLine:
        yield "success: server paused\n"
    while True:
        activeUsers, waitingUsers, isPaused = impl.ezid.getStatus()
        s = (
            f"STATUS {'paused' if isPaused else 'running'} "
            f"activeOperations={sum(activeUsers.values())} "
            f"waitingRequests={sum(waitingUsers.values())} "
            f"binderQueueLength={impl.statistics.getBinderQueueLength()} "
            f"dataciteQueueLength={impl.statistics.getDataCiteQueueLength()} "
            "\n"
        )
        yield s
        time.sleep(3)


def pause(request):
    """Pause or unpause the server

    If the server is paused, server status records are streamed back to
    the client indefinitely.
    """
    if request.method != "GET":
        return _methodNotAllowed()
    user = impl.userauth.authenticateRequest(request)
    if type(user) is str:
        return _response(user)
    elif user is None:
        return _unauthorized()
    elif not user.isSuperuser:
        return _forbidden()
    options = _validateOptions(request, {"op": ["on", "idlewait", "off", "monitor"]})
    if type(options) is str:
        return _response(options)
    if "op" not in options:
        return _response("error: bad request - no 'op' parameter")
    if options["op"] == "on":
        impl.ezid.pause(True)
        return django.http.StreamingHttpResponse(
            _statusLineGenerator(True), content_type="text/plain; charset=utf-8"
        )
    elif options["op"] == "idlewait":
        impl.ezid.pause(True)
        while True:
            activeUsers, waitingUsers, isPaused = impl.ezid.getStatus()
            if len(activeUsers) == 0:
                break
            time.sleep(1)
        return _response("success: server paused and idle")
    elif options["op"] == "off":
        impl.ezid.pause(False)
        return _response("success: server unpaused")
    elif options["op"] == "monitor":
        return django.http.StreamingHttpResponse(
            _statusLineGenerator(False), content_type="text/plain; charset=utf-8"
        )
    else:
        assert False, "unhandled case"


def resolveIdentifier(
    request: django.http.HttpRequest, identifier: str
) -> django.http.HttpResponse:
    '''
    Performs ARK identifier resolution.

    identifier is the path portion of the request after 'ark:'.

    If an EZID identifier, shoulder, or super shoulder matches the start of
    the identifier string, then:
      if the request query contains a single "?"
        return infection info on the matched entry
      else
        return a redirect to the identifier.

    The redirect URL is the request "identifier [+ querystring]" appended to the
    identifier target. If the identifier is flagged as unavailable, then the
    tombstone page is the redirect target.

    The Last-Modified header of the response is set to the date updated of the
    matching identifier.

    The response content body is a JSON block containing the keys:
      id: The matched identifier value
      suffix: The suffix portion of the request, including query string if any
      location: The redirection target URL
      modified: The identifier date updated value

    If the identifier is invalid, then a 404 response is returned, with a JSON body
    with the keys:
      id: The requested identifier value
      error: A brief description of the reason

    If the identifier is valid but not present or reserved, a 404 response is
    returned with a JSON body contining the keys:
      id: The requested identifier value
      error: "Not found."
      alternate: A suggested alternate location to try (N2T url)
    '''
    L = logging.getLogger()
    if django.conf.settings.DEBUG:
        # This is an expensive call so hide it unless debugging
        L.debug("%s.%s: %s", __name__, sys._getframe().f_code.co_name, identifier)
    L.debug(request.get_full_path())

    # Use the request full path to get the requested identifier
    # Note that this requires the resolver operation is located at the service root.
    identifier = request.get_full_path().lstrip("/")
    msg = {"request_id": identifier}

    # construct an identifier parser
    identifier_info = impl.resolver.IdentifierParser.parse(identifier)
    if identifier_info.inflection:
        '''
        Inflection request. 
        Return the metadata about the identifier.        
        '''
        accept_type = impl.http_accept_types.get_best_match(
            request.headers.get('Accept', 'text/plain'),
            impl.http_accept_types.MEDIA_HTML + impl.http_accept_types.MEDIA_JSON + impl.http_accept_types.MEDIA_TEXT
        )
        user = impl.userauth.authenticateRequest(request)
        if isinstance(user, str):
            # This follows legacy behavior, with methods exhibiting a confusing, obfuscated duality
            return _response(user)
        if user is None:
            user = ezidapp.models.user.AnonymousUser
        try:
            pid_record = identifier_info.find_record()
            if not impl.policy.authorizeView(user, pid_record):
                # not authorized
                msg["error"] = "Not authorized"
                return django.http.HttpResponseForbidden(json.dumps(msg), content_type="application/json; charset=utf-8")
            pid_metadata = pid_record.toLegacy()
            # wtf? convertLegacyToExternal modifies the dict in place...
            ezidapp.models.model_util.convertLegacyToExternal(pid_metadata)
            if accept_type in impl.http_accept_types.MEDIA_JSON:
                return django.http.JsonResponse(pid_metadata, json_dumps_params={"indent":2})
            anvl = impl.anvl.format(pid_metadata)
            return django.http.HttpResponse(anvl, content_type="text/plain")

        except ezidapp.models.identifier.Identifier.DoesNotExist:
            # identifier not found here
            # Let's try matching a shoulder
            shoulder_record = identifier_info.find_shoulder()
            if shoulder_record is None:
                msg["error"] = "Not found."
                msg["alternate"] = f"https://n2t.net/{identifier}"
                return django.http.HttpResponseNotFound(msg, content_type="application/json; charset=utf-8")
            msg["id"] = shoulder_record.prefix
            msg["erc.who"] = shoulder_record.name
            msg["erc.what"] = shoulder_record.shoulder_type.shoulder_type
            msg["erc.when"] = shoulder_record.date.isoformat()
            msg["agency"] = shoulder_record.registration_agency.registration_agency
            if accept_type in impl.http_accept_types.MEDIA_JSON:
                return django.http.JsonResponse(msg, json_dumps_params={"indent":2})
            anvl = impl.anvl.format(msg)
            return django.http.HttpResponse(anvl)
        except Exception as e:
            msg["error"] = "Invalid or unrecognized identifier"
        return django.http.HttpResponseNotFound(
            json.dumps(msg), content_type="application/json; charset=utf-8"
        )
    # Handle resolve request
    # If the identifier is a DOI, then redirect to the registered DOI resolver
    if identifier_info.scheme == impl.resolver.SCHEME_DOI:
        try:
            doi_resolver = django.conf.settings.RESOLVER_DOI
        except:
            doi_resolver = "https://doi.org/"
        return django.http.HttpResponseRedirect(f"{doi_resolver}{identifier_info.prefix}/{identifier_info.suffix}{identifier_info.extra}")
    # ARK identifier resolution
    try:
        # Populate the identifier structure but with minimal field info, enough to
        # service the redirect
        res = identifier_info.find_record(fields=["identifier","updateTime","target","status"])
        if res.isReserved:
            # A reserved identifier is not resolvable
            raise ValueError
        t_modified = datetime.datetime.fromtimestamp(res.updateTime, tz=datetime.timezone.utc)
        headers = {"Last-Modified": t_modified.strftime(HTTP_DATE_FORMAT)}
        msg["id"] = res.identifier
        msg["scheme"] = identifier_info.scheme
        msg["prefix"] = identifier_info.prefix
        msg["suffix"] = identifier_info.suffix
        msg["extra"] = identifier_info.extra
        # identifier.resolverTarget checks for unavailable status and returns
        # the appropriate URL for the identifier target. e.g. the tombstone address vs. registered location
        msg['location'] = f"{res.resolverTarget}{identifier_info.extra}"
        msg['modified'] = t_modified.isoformat()
        return django.http.HttpResponseRedirect(
            msg["location"],
            headers=headers,
            content= json.dumps(msg, indent=2),
            content_type="application/json; charset=utf-8",
        )
    except ValueError:
        # invalid identifier
        msg["error"] = "Invalid, unrecognized, or reserved identifier."
    except ezidapp.models.identifier.Identifier.DoesNotExist:
        # identifier not found here
        msg["error"] = "Not found."
        msg["alternate"] = f"https://n2t.net/{identifier}"
    except Exception as e:
        L.error(e)
        msg["error"] = "Not found."
    return django.http.HttpResponseNotFound(
        json.dumps(msg), content_type="application/json; charset=utf-8"
    )
