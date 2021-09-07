#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import hashlib
import re
import sys
import threading
import time

import django.conf

import ezidapp.models.async_queue
import ezidapp.models.group
import ezidapp.models.user
import ezidapp.models.util
import impl.log
import impl.policy
import impl.util

_usedFilenames = []

SUFFIX_FORMAT_DICT = {
    ezidapp.models.async_queue.DownloadQueue.ANVL: "txt",
    ezidapp.models.async_queue.DownloadQueue.CSV: "csv",
    ezidapp.models.async_queue.DownloadQueue.XML: "xml",
}

_lock = threading.Lock()

import logging

log = logging.getLogger(__name__)


def enqueueRequest(state, user, request):
    """Enqueue a batch download request

    The request must be authenticated; 'user' should be a User object.

    'request' should be a django.http.QueryDict object (from a POST request or manually created) containing the parameters
    of the request.  The available parameters are described in the API documentation.  One feature
    not mentioned in the documentation: for the 'notify' parameter, an email address may be a
    straight address ("fred@slate.com") or may include an addressee name ("Fred Flintstone
    <fred@slate.com>"); in the latter case a salutation line will be added to the email message.

    The successful return is a string that includes the download URL, as
    in:

      success: https://ezid.cdlib.org/download/da543b91a0.xml.gz

    Unsuccessful returns include the strings:

      error: forbidden
      error: bad request - subreason...
      error: internal server error
    """

    state = {
        # name: (repeatable, validator)
        "column": (True, _validateString),
        "convertTimestamps": (False, _validateBoolean),
        "createdAfter": (False, _validateTimestamp),
        "createdBefore": (False, _validateTimestamp),
        "crossref": (False, _validateBoolean),
        "datacite": (False, _validateBoolean),
        "exported": (False, _validateBoolean),
        "format": (
            False,
            lambda v: _validateEnumerated(v, ["anvl", "csv", "xml"]),
        ),
        "compression": (
            False,
            lambda v: _validateEnumerated(v, ["gzip", "zip"]),
        ),
        "notify": (True, _validateString),
        "owner": (True, _validateUser),
        "ownergroup": (True, _validateGroup),
        "permanence": (
            False,
            lambda v: _validateEnumerated(v, ["test", "real"]),
        ),
        "profile": (True, _validateString),
        "status": (
            True,
            lambda v: _validateEnumerated(v, ["reserved", "public", "unavailable"]),
        ),
        "type": (
            True,
            lambda v: _validateEnumerated(v, ["ark", "doi", "uuid"]),
        ),
        "updatedAfter": (False, _validateTimestamp),
        "updatedBefore": (False, _validateTimestamp),
    }
    _formatCode = {
        "anvl": ezidapp.models.async_queue.DownloadQueue.ANVL,
        "csv": ezidapp.models.async_queue.DownloadQueue.CSV,
        "xml": ezidapp.models.async_queue.DownloadQueue.XML,
    }

    SUFFIX_FORMAT_DICT = {
        ezidapp.models.async_queue.DownloadQueue.ANVL: "txt",
        ezidapp.models.async_queue.DownloadQueue.CSV: "csv",
        ezidapp.models.async_queue.DownloadQueue.XML: "xml",
    }

    _compressionCode = {
        "gzip": ezidapp.models.async_queue.DownloadQueue.GZIP,
        "zip": ezidapp.models.async_queue.DownloadQueue.ZIP,
    }
    _usedFilenames = []

    def error(s):
        return "error: bad request - " + s

    try:
        d = {}
        for k in request:
            if k not in state:
                return error("invalid parameter: " + impl.util.oneLine(k))
            try:
                if state[k][0]:
                    d[k] = list(map(state[k][1], request.getlist(k)))
                else:
                    if len(request.getlist(k)) > 1:
                        return error("parameter is not repeatable: " + k)
                    d[k] = state[k][1](request[k])
            except _ValidationException as e:
                return error(f"parameter '{k}': {str(e)}")
        if "format" not in d:
            return error("missing required parameter: format")
        format = d["format"]
        del d["format"]
        if "compression" in d:
            compression = d["compression"]
            del d["compression"]
        else:
            compression = "gzip"
        if format == "csv":
            if "column" not in d:
                return error("format 'csv' requires at least one column")
            columns = d["column"]
            del d["column"]
        else:
            if "column" in d:
                return error("parameter is incompatible with format: column")
            columns = []
        toHarvest = []
        if "owner" in d:
            for o in d["owner"]:
                if not impl.policy.authorizeDownload(user, owner=o):
                    return "error: forbidden"
                if o.pid not in toHarvest:
                    toHarvest.append(o.pid)
            del d["owner"]
        if "ownergroup" in d:
            for g in d["ownergroup"]:
                if not impl.policy.authorizeDownload(user, ownergroup=g):
                    return "error: forbidden"
                for u in g.users.all():
                    if u.pid not in toHarvest:
                        toHarvest.append(u.pid)
            del d["ownergroup"]
        if len(toHarvest) == 0:
            toHarvest = [user.pid]
        if "notify" in d:
            notify = d["notify"]
            del d["notify"]
        else:
            notify = []
        if "convertTimestamps" in d:
            options = {"convertTimestamps": d["convertTimestamps"]}
            del d["convertTimestamps"]
        else:
            options = {"convertTimestamps": False}
        requestor = user.pid
        filename = _generateFilename(requestor)
        r = ezidapp.models.async_queue.DownloadQueue(
            requestTime=int(time.time()),
            rawRequest=request.urlencode(),
            requestor=requestor,
            format=_formatCode[format],
            compression=_compressionCode[compression],
            columns=encode(columns),
            constraints=encode(d),
            options=encode(options),
            notify=encode(notify),
            filename=filename,
            toHarvest=",".join(toHarvest),
        )
        r.save()
        return f"success: {django.conf.settings.EZID_BASE_URL}/download/{filename}.{_fileSuffix(r)}"
    except Exception as e:
        impl.log.otherError("download.enqueueRequest", e)
        if sys.is_running_under_pytest:
            raise
        return "error: internal server error"


def _validateString(v):
    s = v.strip()
    if s == "":
        raise _ValidationException("empty value")
    return s


def _validateEnumerated(v, l):
    if v not in l:
        raise _ValidationException("invalid parameter value")
    return v


def _validateBoolean(v):
    return _validateEnumerated(v, ["yes", "no"]) == "yes"


def _validateTimestamp(v):
    try:
        try:
            return impl.util.parseTimestampZulu(v)
        except Exception:
            return int(v)
    except Exception:
        raise _ValidationException("invalid timestamp")


def _validateUser(v):
    u = ezidapp.models.util.getUserByUsername(v)
    if u is not None and not u.isAnonymous:
        return u
    else:
        raise _ValidationException("no such user")


def _validateGroup(v):
    g = ezidapp.models.util.getGroupByGroupname(v)
    if g is not None and not g.isAnonymous:
        return g
    else:
        raise _ValidationException("no such group")


def _generateFilename(requestor):
    while True:
        f = hashlib.sha1(
            f"{requestor},{str(time.time())},{django.conf.settings.SECRET_KEY}"
        ).hexdigest()[::4]
        _lock.acquire()
        try:
            if f not in _usedFilenames:
                # noinspection PyUnresolvedReferences
                _usedFilenames.append(f)
                return f
        finally:
            _lock.release()


# A simple encoding mechanism for storing Python objects as strings
# follows.  We could use pickling, but this technique makes debugging
# a little easier.


def _escape(s):
    return re.sub("[%,=]", lambda c: f"%{ord(c.group(0)):02X}", s)


def encode(o):
    if type(o) is bool:
        return "B" + str(o)
    elif type(o) is int:
        return "I" + str(o)
    elif type(o) in [str, str]:
        return "S" + o
    elif type(o) is list:
        return "L" + ",".join([_escape(encode(i)) for i in o])
    elif type(o) is dict:
        return "D" + ",".join(
            map(
                lambda kv: f"{_escape(encode(kv[0]))}={_escape(encode(kv[1]))}",
                list(o.items()),
            )
        )
    else:
        assert False, "unhandled case"


def _unescape(s):
    return re.sub("%([0-9A-F][0-9A-F])", lambda m: chr(int(m.group(1), 16)), s)


def _decode(s):
    if s[0] == "B":
        return s[1:] == "True"
    elif s[0] == "I":
        return int(s[1:])
    elif s[0] == "S":
        return s[1:]
    elif s[0] == "L":
        if len(s) > 1:
            return [_decode(_unescape(i)) for i in s[1:].split(",")]
        else:
            return []
    elif s[0] == "D":
        if len(s) > 1:
            return dict(
                list(
                    map(
                        lambda i: tuple(
                            [_decode(_unescape(kv)) for kv in i.split("=")]
                        ),
                        s[1:].split(","),
                    )
                )
            )
        else:
            return {}
    else:
        assert False, "unhandled case"


def _fileSuffix(r):
    if r.compression == ezidapp.models.async_queue.DownloadQueue.GZIP:
        return SUFFIX_FORMAT_DICT[r.format] + ".gz"
    else:
        return "zip"


class _ValidationException(Exception):
    pass
