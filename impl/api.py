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
import os
import ast
import datetime
import json
import logging
import sys
import time
import typing

import django.conf
import django.http

import ezidapp.models.identifier
import ezidapp.models.model_util
import ezidapp.models.shoulder

import impl.anvl
import impl.datacite
import impl.download
import impl.ezid
import impl.resolver
import impl.search_util
import impl.statistics
import impl.userauth
import impl.util
import impl.http_accept_types
import impl.s3

HTTP_DATE_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"


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
    mimetype = None
    charset = None
    if ';' in content_type:
        [mimetype, charset] = content_type.split(';')
        mimetype = mimetype.strip()
        charset = charset.split('=')[1].strip()
    else:
        mimetype = content_type.strip()

    print(mimetype)
    print(charset)

    if mimetype not in ('text/plain', ''):
        return False
    if charset is not None and charset.lower() != 'utf-8':
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
            l = "datacite,search"
        for ss in [ss.strip() for ss in l.split(",") if len(ss.strip()) > 0]:
            if ss == "datacite":
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


def identifier_metadata(identifier_record: ezidapp.models.identifier.Identifier) -> dict:
    '''Given an identifier record, generate a dict that may be serialized to ANVL or JSON.

    This method is separate from ezid.getMetadata because that method assumes input of
    an identifier string and performs validation and so forth.

    Also, here we try to represent the different metadata serializations in a way that
    can conform with the requested media type by returning a metadata dict that can be
    serialzied to ANVL or JSON.
    '''

    def date_convert(dt_str: str) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(int(dt_str))

    L = logging.getLogger("identifier_metadata")
    meta_dict = identifier_record.toLegacy()
    # Make the metadata a standalone dict
    _profile = identifier_record.profile.label
    L.debug("profile: %s", _profile)
    L.debug("metadata: %s", meta_dict)
    if "erc" in meta_dict:
        _tmp = impl.anvl.parse(meta_dict.pop('erc'))
        meta_dict["erc"] = _tmp
    # _tmp_dict = {}
    # for k,v in meta_dict.items():
    #    kparts = k.split(".", 1)
    #    if len(kparts) > 1:
    #        if kparts[0] not in _tmp_dict:
    #            _tmp_dict[kparts[0]] = {}
    #        _tmp_dict[kparts[0]][kparts[1]] = v
    #    else:
    #        _tmp_dict[k] = v

    if not _profile in meta_dict:
        # The metadata exists as "profile.key" entries
        # Restructure to make it a dict under a profile key
        _tmp_dict = {_profile: {}}
        if _profile != "erc":
            _tmp_dict["erc"] = {}
        if _profile != "dc":
            _tmp_dict["dc"] = {}
        _test = f"{_profile}."
        _test_len = len(_test)
        for k in meta_dict:
            if k.startswith(f"{_profile}."):
                v = meta_dict[k]
                _tmp_dict[_profile][k[_test_len:]] = v
            elif k.startswith("erc."):
                _tmp_dict["erc"][k[4:]] = meta_dict[k]
            elif k.startswith("dc."):
                _tmp_dict["erc"][k[3:]] = meta_dict[k]
            else:
                _tmp_dict[k] = meta_dict[k]
        if len(_tmp_dict["erc"]) == 0:
            _tmp_dict.pop("erc")
        if len(_tmp_dict["dc"]) == 0:
            _tmp_dict.pop("dc")
        if len(_tmp_dict.get(_profile, {})) > 0:
            meta_dict = _tmp_dict
    else:
        if identifier_record.usesSchemaOrgProfile:  # schema_org
            # The metadata is a dict but not stored according to json spec
            if _profile in meta_dict:
                try:
                    _tmp = ast.literal_eval(meta_dict.pop('schema_org'))
                    meta_dict['schema_org'] = _tmp
                except Exception as e:
                    L.warning(
                        "Unable to parse schema_org metadata for %s", identifier_record.identifier
                    )
    ezidapp.models.model_util.convertLegacyToExternal(meta_dict)
    try:
        meta_dict["id created"] = date_convert(meta_dict.pop("_created"))
    except Exception as e:
        L.error(e)
    try:
        meta_dict["id updated"] = date_convert(meta_dict.pop("_updated"))
    except Exception as e:
        L.error(e)
    return meta_dict


def generate_response(
    request: django.http.HttpRequest,
    message: dict,
    status: int = 200,
    headers: typing.Optional[dict] = None,
) -> django.http.HttpResponse:
    L = logging.getLogger()
    # Check for requested response format
    # Default response is text/plain
    content_type = impl.http_accept_types.get_best_match(
        request.headers.get('Accept', 'application/json'), impl.http_accept_types.MEDIA_INFLECTION
    )
    L.debug("Accept = %s", content_type)
    if content_type in (impl.http_accept_types.MEDIA_JSON + impl.http_accept_types.MEDIA_ANY):
        if status >= 300 and status < 400:
            return django.http.HttpResponseRedirect(
                message["location"],
                headers=headers,
                content=json.dumps(message, indent=2),
                content_type="application/json; charset=utf-8",
            )
        return django.http.JsonResponse(
            message,
            status=status,
            content_type="application/json; charset=utf-8",
            json_dumps_params={"indent": 2},
            headers=headers,
        )
    _message = {}
    for k, v in message.items():
        if isinstance(v, dict):
            if k == "schema_org":
                _message[k] = json.dumps(v)
            else:
                _message[k] = v
        else:
            _message[k] = v
    if status >= 300 and status < 400:
        return django.http.HttpResponseRedirect(
            message["location"],
            headers=headers,
            content=impl.anvl.format(_message),
            content_type="text/plain; charset=utf-8",
        )
    return django.http.HttpResponse(
        impl.anvl.format(_message),
        status=status,
        content_type="text/plain; charset=utf-8",
        headers=headers,
    )


def resolveInflection(
    request: django.http.HttpRequest, identifier_info: impl.resolver.IdentifierStruct
) -> django.http.HttpResponse:
    '''"inflection" is a request for information about the identifier.

    This is similar to the /id/ (getMetadata) operation in EZID, but here the
    ANVL output is more aligned with that produced by N2T and the response may
    also be provided in JSON is requested through content negotiation.
    '''
    L = logging.getLogger()
    user = impl.userauth.authenticateRequest(request)
    msg = {}
    if isinstance(user, str):
        # This follows legacy behavior, with methods exhibiting a confusing, obfuscated duality
        # In this case, if user is a str, then it's some sort of error condition
        status = _statusMapping(user, False)
        msg_parts = user.split(":", 1)
        # Python preserves dict item order, which is helpful if the
        # response is anvl
        msg = {"error": msg_parts[1], "identifier": identifier_info.original}
        return generate_response(request, msg, status=status)
    # No user is same as anonymous
    if user is None:
        user = ezidapp.models.user.AnonymousUser
    try:
        # Get the database entry. This will throw if not found
        pid_record = identifier_info.find_record()
        if not impl.policy.authorizeView(user, pid_record):
            # not authorized
            msg = {
                "error": "unauthorized",
                "identifier": identifier_info.original,
            }
            return generate_response(request, msg, status=401)
        pid_metadata = identifier_metadata(pid_record)
        t_modified = datetime.datetime.fromtimestamp(
            pid_record.updateTime, tz=datetime.timezone.utc
        )
        headers = {"Last-Modified": t_modified.strftime(HTTP_DATE_FORMAT)}
        return generate_response(request, pid_metadata, status=200, headers=headers)

    except ezidapp.models.identifier.Identifier.DoesNotExist:
        # identifier not found here
        # Let's try matching a shoulder
        try:
            shoulder_record = identifier_info.find_shoulder()
        except ezidapp.models.shoulder.Shoulder.DoesNotExist:
            # OK, let's look for the NAAN and report the shoulders.
            try:
                shoulders = identifier_info.find_shoulders()
                msg = {}
                for shoulder in shoulders:
                    msg[shoulder.prefix] = {
                        "erc.who": shoulder.name,
                        "erc.what": shoulder.type,
                        "erc.when": shoulder.date,
                    }
                return generate_response(request, msg, status=200)
            except ezidapp.models.shoulder.Shoulder.DoesNotExist:
                pass
            # naans = ezidapp.models.shoulder.list_naans(shoulder_type="ARK")
            # print(naans)
            msg = {
                "error": "not found",
                "identifier": identifier_info.original,
                "alternate": f"https://n2t.net/{identifier_info.original}",
            }
            return generate_response(request, msg, status=404)
        msg = {
            "id": shoulder_record.prefix,
            "erc.who": shoulder_record.name,
            "erc.what": "shoulder"
            if shoulder_record.shoulder_type is None
            else shoulder_record.shoulder_type.shoulder_type,
            "erc.when": shoulder_record.date.isoformat(),
            "agency": "ezid"
            if shoulder_record.registration_agency is None
            else shoulder_record.registration_agency.registration_agency,
        }
        # Note there is no date-modified for shoulders
        return generate_response(request, msg, status=200)
    except Exception as e:
        L.error("resolveInflection error: %s", e)
        msg = {"error": "unable to parse", "identifier": identifier_info.original}
    return generate_response(request, msg, status=400)


def resolveIdentifier(
    request: django.http.HttpRequest, identifier: str
) -> django.http.HttpResponse:
    '''
    Performs identifier resolution and inflection.

    identifier is the path portion of the request after 'ark:' or 'doi:',
    however, note that identifier string is not used here, but instead the
    full path of the request is evaluated. This is because the full path
    may contain additional information (inflection and suffix for passthrough)
    that will normally be stripped out by the Django variable parsing mechanism.

    The following steps are performed:

    1. The identifier is parsed to an IdentifierStruct.
    2. If the request is an inflection request then:
    2.1. If the identifier is in the database then:
    2.1.1. Metadata is retrieved
    2.1.2. Response as ANVL or JSON according to content negotiation
    2.2. If the identifier matches a shoulder then:
    2.2.1. Shoulder metadata constructed
    2.2.2. Returned as ANVL or JSON according to content negotiation
    2.3. A not found error is returned
    3. The request is a resolve request
    4. If the identifier is a DOI:
    4.1. If No-Redirect is not requested (default):
    4.1.1. Redirect to the DOI resolver service
    5. If the identifier is not in the database:
    5.1. An HTTP 404 Not Found error is returned
    6. If the identifier is in the database:
    6.1. If the identifier is reserved:
    6.1.1. Return a 404 http status
    6.2. Gather minimal metadata about the identifier
    6.3. If No-redirect is not requested (default)
    6.3.1. Return a redirect response containing the minimal metadata as a body. If
         the identifier is flagged as unavailable, then the tombstone page is the
         redirect target.
    6.4. Return the minimal metadata about the identifier

    Response from this method is one of:

    - http redirect to target
    - response body containing metadata associated with the identifier
    - A 404 not found error
    - A 401 not authorized error

    An inflection request versus a redirect request is distinguished by the
    presence of terminating "?", "??", or "?info" characters on the full path.

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
    returned with a JSON body containing the keys:
      id: The requested identifier value
      error: "Not found."
      alternate: A suggested alternate location to try (N2T url)

    If the client issues a request with the custom header "No-Redirect", then
    the response is either an ANVL or JSON (by content-negotiation) representation
    of the minimal metadata about the identifier.
    '''
    L = logging.getLogger(__name__)
    if django.conf.settings.DEBUG:
        # This is an expensive call so hide it unless debugging
        L.debug("%s.%s: %s", __name__, sys._getframe().f_code.co_name, identifier)
    L.debug(request.get_full_path())

    # Use the request full path to get the requested identifier
    # Note that this requires the resolver operation is located at the service root.
    identifier = request.get_full_path().lstrip("/")

    # Use the IdentifierParser to parse and get an identifier structure
    identifier_info = impl.resolver.IdentifierParser.parse(identifier)
    if identifier_info.inflection:
        return resolveInflection(request, identifier_info)

    # Check to see if client has requested no-redirects through the custom No-redirect header
    follow_redirect = not impl.util.truthy_to_boolean(request.headers.get("No-Redirect", False))
    msg = {"request_id": identifier}
    # Handle resolve request
    # If the identifier is a DOI, then redirect to the registered DOI resolver
    # Don't even bother to look for
    if identifier_info.scheme == impl.resolver.SCHEME_DOI and follow_redirect:
        try:
            doi_resolver = django.conf.settings.RESOLVER_DOI
            if not doi_resolver.endswith("/"):
                doi_resolver = doi_resolver + "/"
        except:
            doi_resolver = "https://doi.org/"
        return django.http.HttpResponseRedirect(
            f"{doi_resolver}{identifier_info.prefix}/{identifier_info.suffix}{identifier_info.extra}"
        )
    # Retrieve the identifier info to support redirection or inspection of metadata about the identifier
    try:
        # Populate the identifier structure but with minimal field info, enough to
        # service the redirect
        res = identifier_info.find_record(fields=["identifier", "updateTime", "target", "status"])
        if res.isReserved:
            # A reserved identifier is not resolvable
            raise ValueError
        t_modified = datetime.datetime.fromtimestamp(res.updateTime, tz=datetime.timezone.utc)
        headers = {"Last-Modified": t_modified.strftime(HTTP_DATE_FORMAT)}
        msg["id"] = res.identifier
        msg["extra"] = identifier_info.extra
        # identifier.resolverTarget checks for unavailable status and returns
        # the appropriate URL for the identifier target. e.g. the tombstone address vs. registered location
        msg['location'] = f"{res.resolverTarget}{identifier_info.extra}"
        msg['modified'] = t_modified
        # Check for custom No-Redirect header value
        if not follow_redirect:
            headers["Location"] = msg["location"]
            return generate_response(request, msg, status=200, headers=headers)
        # Convert date time to a string for the redirect body
        msg['modified'] = t_modified.isoformat()
        return generate_response(request, msg, status=302, headers=headers)
        # return django.http.HttpResponseRedirect(
        #    msg["location"],
        #    headers=headers,
        #    content= json.dumps(msg, indent=2),
        #    content_type="application/json; charset=utf-8",
        # )
    except ValueError:
        # invalid identifier
        msg["error"] = "Invalid, unrecognized, or reserved identifier."
    except ezidapp.models.identifier.Identifier.DoesNotExist:
        # identifier not found here
        msg["error"] = "Not found."
        _arkresolver = django.conf.settings.RESOLVER_ARK
        if not _arkresolver.endswith("/"):
            _arkresolver += "/"
        msg["alternate"] = f"{_arkresolver}{identifier}"
    except Exception as e:
        L.error(e)
        msg["error"] = "Not found."
    return django.http.HttpResponseNotFound(
        json.dumps(msg), content_type="application/json; charset=utf-8"
    )

def s3_download(request):
    L = logging.getLogger()
    file_path = request.path_info
    prefix, filename = os.path.split(file_path)
    bucket_name = django.conf.settings.S3_BUCKET
    object_key = f"{django.conf.settings.S3_BUCKET_DOWNLOAD_PATH}/{filename}"
    pre_signed_url = impl.s3.generate_presigned_url(bucket_name, object_key)
    L.info(f"Pre-signed URL for {object_key} : {pre_signed_url}")

    return django.http.HttpResponseRedirect(pre_signed_url)
