# =============================================================================
#
# EZID :: download.py
#
# Batch download.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import calendar
import django.conf
import exceptions
import hashlib
import os.path
import re
import time

import config
import ezidapp
import idmap
import log
import search

_ezidUrl = None

def _loadConfig ():
  global _ezidUrl
  _ezidUrl = config.config("DEFAULT.ezid_base_url")

_suffix = {
  "anvl": "txt",
  "csv": "csv",
  "xml": "xml"
}

def _oneline (s):
  return re.sub("\s", " ", s)

class _ValidationException (Exception):
  pass

def _validateString (v):
  s = v.strip()
  if s == "": raise _ValidationException("empty value")
  return s

def _validateEnumerated (v, l):
  if v not in l: raise _ValidationException("invalid parameter value")
  return v

def _validateBoolean (v):
  return (_validateEnumerated(v, ["yes", "no"]) == "yes")

def _validateTimestamp (v):
  try:
    try:
      return calendar.timegm(time.strptime(v, "%Y-%m-%dT%H:%M:%SZ"))
    except:
      return int(v)
  except:
    raise _ValidationException("invalid timestamp")

def _validateUser (v):
  try:
    return idmap.getUserId(v)
  except Exception, e:
    if type(e) is exceptions.AssertionError and "unknown user" in e.message:
      raise _ValidationException("no such user")
    else:
      raise

def _validateGroup (v):
  try:
    return idmap.getGroupId(v)
  except Exception, e:
    if type(e) is exceptions.AssertionError and "unknown group" in e.message:
      raise _ValidationException("no such group")
    else:
      raise

# A simple encoding mechanism for storing Python objects as strings
# follows.  We could use pickling, but this technique makes debugging
# a little easier.

def _escape (s):
  return re.sub("[%,=]", lambda c: "%%%02X" % ord(c.group(0)), s)

def _encode (o):
  if type(o) is bool:
    return "B" + str(o)
  elif type(o) is int:
    return "I" + str(o)
  elif type(o) in [str, unicode]:
    return "S" + o
  elif type(o) is list:
    return "L" + ",".join(map(lambda i: _escape(_encode(i)), o))
  elif type(o) is dict:
    return "D" + ",".join(map(lambda kv: "%s=%s" % (_escape(_encode(kv[0])),
      _escape(_encode(kv[1]))), o.items()))
  else:
    assert False, "unhandled case"

def _unescape (s):
  return re.sub("%([0-9A-F][0-9A-F])", lambda m: chr(int(m.group(1), 16)), s)

def _decode (s):
  if s[0] == "B":
    return (s[1:] == "True")
  elif s[0] == "I":
    return int(s[1:])
  elif s[0] == "S":
    return s[1:]
  elif s[0] == "L":
    if len(s) > 1:
      return map(lambda i: _decode(_unescape(i)), s[1:].split(","))
    else:
      return []
  elif s[0] == "D":
    if len(s) > 1:
      return dict(map(lambda i: tuple(map(lambda kv: _decode(_unescape(kv)),
        i.split("="))), s[1:].split(",")))
    else:
      return {}
  else:
    assert False, "unhandled case"

_parameters = {
  # name: (repeatable, validator)
  "column": (True, _validateString),
  "convertTimestamps": (False, _validateBoolean),
  "createdAfter": (False, _validateTimestamp),
  "createdBefore": (False, _validateTimestamp),
  "crossref": (False, _validateBoolean),
  "exported": (False, _validateBoolean),
  "format": (False, lambda v: _validateEnumerated(v, ["anvl", "csv", "xml"])),
  "notify": (True, _validateString),
  "owner": (True, _validateUser),
  "ownergroup": (True, _validateGroup),
  "permanence": (False, lambda v: _validateEnumerated(v, ["test", "real"])),
  "profile": (True, _validateString),
  "status": (True, lambda v: _validateEnumerated(v, ["reserved", "public",
    "unavailable"])),
  "type": (True, lambda v: _validateEnumerated(v, ["ark", "doi", "urn"])),
  "updatedAfter": (False, _validateTimestamp),
  "updatedBefore": (False, _validateTimestamp)
}

def _generateFilename (requestor):
  return hashlib.sha1("%s,%s,%s" % (requestor, str(time.time()),
    django.conf.settings.SECRET_KEY)).hexdigest()[::4]

def enqueueRequest (auth, request):
  """
  Enqueues a batch download request.  The request must be
  authenticated; 'auth' should be a userauth.AuthenticatedUser object.
  'request' should be an HTTP GET request.  The successful return is a
  string that includes the download URL, as in:

    success: http://ezid.cdlib.org/download/da543b91a0.xml.gz

  Unsuccessful returns include the strings:

    error: bad request - subreason...
    error: internal server error
  """
  def error (s):
    return "error: bad request - " + s
  try:
    d = {}
    for k in request.GET:
      if k not in _parameters:
        return error("invalid parameter: " + _oneline(k))
      try:
        if _parameters[k][0]:
          d[k] = map(_parameters[k][1], request.GET.getlist(k))
        else:
          if len(request.GET.getlist(k)) > 1:
            return error("parameter is not repeatable: " + k)
          d[k] = _parameters[k][1](request.GET[k])
      except _ValidationException, e:
        return error("parameter '%s': %s" % (k, str(e)))
    if "format" not in d:
      return error("missing required parameter: format")
    format = d["format"]
    del d["format"]
    if format == "csv":
      if "column" not in d:
        return error("format 'csv' requires at least one column")
      columns = d["column"]
      del d["column"]
    else:
      if "column" in d:
        return error("parameter is incompatible with format: column")
      columns = []
    if "notify" in d:
      notify = d["notify"]
      del d["notify"]
    else:
      notify = []
    if "convertTimestamps" in d:
      options = { "convertTimestamps": d["convertTimestamps"] }
      del d["convertTimestamps"]
    else:
      options = { "convertTimestamps": False }
    requestor = auth.user[1]
    filename = _generateFilename(requestor)
    r = ezidapp.models.DownloadQueue(requestTime=int(time.time()),
      requestor=requestor, coOwners=",".join(search.getCoOwnership(requestor)),
      format=format, columns=_encode(columns), constraints=_encode(d),
      options=_encode(options), notify=_encode(notify), filename=filename)
    r.save()
    return "success: %s/download/%s.%s.gz" % (_ezidUrl, filename,
      _suffix[format])
  except Exception, e:
    log.otherError("download.enqueueRequest", e)
    return "error: internal server error"

_loadConfig()
config.addLoader(_loadConfig)
