# =============================================================================
#
# EZID :: download.py
#
# Batch download.
#
# Downloads are created by a single daemon thread.  The download
# creation process is designed to be restartable at any point: if the
# server is restarted, the current download resumes where it left off.
#
# When the server is reloaded, a new daemon thread gets created.  Race
# conditions exist between the old and new threads while the old
# thread still exists, but actual conflicts should be very unlikely.
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
import csv
import django.conf
import django.core.mail
import exceptions
import hashlib
import os
import os.path
import re
import subprocess
import threading
import time
import uuid

import config
import ezidapp.models
import idmap
import log
import search

_ezidUrl = None
_usedFilenames = None
_lock = threading.Lock()
_daemonEnabled = None
_threadName = None
_idleSleep = None
_gzipCommand = None

def _loadConfig ():
  global _ezidUrl, _usedFilenames, _daemonEnabled, _threadName, _idleSleep
  global _gzipCommand
  _ezidUrl = config.config("DEFAULT.ezid_base_url")
  _lock.acquire()
  try:
    if _usedFilenames == None:
      _usedFilenames = [r.filename for r in\
        ezidapp.models.DownloadQueue.objects.all()] +\
        [f.split(".")[0] for f in\
        os.listdir(django.conf.settings.DOWNLOAD_PUBLIC_DIR)]
  finally:
    _lock.release()
  _idleSleep = int(config.config("daemons.download_processing_idle_sleep"))
  _gzipCommand = config.config("DEFAULT.gzip_command")
  _daemonEnabled = (django.conf.settings.DAEMON_THREADS_ENABLED and\
    config.config("daemons.download_enabled").lower() == "true")
  if _daemonEnabled:
    _threadName = uuid.uuid1().hex
    t = threading.Thread(target=_daemonThread, name=_threadName)
    t.setDaemon(True)
    t.start()

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
  while True:
    f = hashlib.sha1("%s,%s,%s" % (requestor, str(time.time()),
      django.conf.settings.SECRET_KEY)).hexdigest()[::4]
    _lock.acquire()
    try:
      if f not in _usedFilenames:
        _usedFilenames.append(f)
        return f
    finally:
      _lock.release()

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
      rawRequest=request.GET.urlencode(),
      requestor=requestor, coOwners=",".join(search.getCoOwnership(requestor)),
      format=format, columns=_encode(columns), constraints=_encode(d),
      options=_encode(options), notify=_encode(notify), filename=filename)
    r.save()
    return "success: %s/download/%s.%s.gz" % (_ezidUrl, filename,
      _suffix[format])
  except Exception, e:
    log.otherError("download.enqueueRequest", e)
    return "error: internal server error"

def getQueueLength ():
  """
  Returns the length of the batch download queue.
  """
  return ezidapp.models.DownloadQueue.objects.count()

class _AbortException (Exception):
  pass

def _checkAbort ():
  # This function provides a handy way to abort processing if the
  # daemon is disabled or if a new daemon thread is started by a
  # configuration reload.  It doesn't entirely eliminate potential
  # race conditions between two daemon threads, but it should make
  # conflicts very unlikely.
  if not _daemonEnabled or threading.currentThread().getName() != _threadName:
    raise _AbortException()

def _wrapException (context, exception):
  m = str(exception)
  if len(m) > 0: m = ": " + m
  return Exception("batch download error: %s: %s%s" % (context,
    type(exception).__name__, m))

def _path (r, i):
  # i=1: uncompressed work file
  # i=2: compressed work file
  # i=3: compressed delivery file
  # i=4: request sidecar file
  if i in [1, 2]:
    d = django.conf.settings.DOWNLOAD_WORK_DIR
  else:
    d = django.conf.settings.DOWNLOAD_PUBLIC_DIR
  if i != 4:
    s = _suffix[r.format]
  else:
    s = "request"
  if i in [2, 3]:
    z = ".gz"
  else:
    z = ""
  return os.path.join(d, "%s.%s%s" % (r.filename, s, z))

def _csvEncode (s):
  return _oneline(s).encode("UTF-8")

def _flushFile (f):
  f.flush()
  os.fsync(f.fileno())

def _createFile (r):
  f = None
  try:
    f = open(_path(r, 1), "wb")
    if r.format == "csv":
      w = csv.writer(f)
      w.writerow([_csvEncode(c) for c in _decode(r.columns)])
      _flushFile(f)
    elif r.format == "xml":
      f.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<records>")
      _flushFile(f)
    # We don't know exactly what the CSV writer wrote, so we must
    # probe the file to find its size.
    n = f.tell()
  except Exception, e:
    raise _wrapException("error creating file", e)
  else:
    r.stage = ezidapp.models.DownloadQueue.HARVEST
    r.currentOwner = r.requestor
    r.fileSize = n
    r.save()
  finally:
    if f: f.close()

def _harvest (r):
  r.stage = ezidapp.models.DownloadQueue.COMPRESS
  r.save()

def _compressFile (r):
  infile = None
  outfile = None
  try:
    infile = open(_path(r, 1))
    # The gzip command may be long-lived, and a new daemon thread may
    # be created by a server restart or reload while gzip is still
    # running, in which case we don't try to kill the old process, but
    # simply delete its output file and let it die a natural death.
    if os.path.exists(_path(r, 2)): os.unlink(_path(r, 2))
    outfile = open(_path(r, 2), "w")
    p = subprocess.Popen([_gzipCommand], stdin=infile, stdout=outfile,
      stderr=subprocess.PIPE, close_fds=True, env={})
    stderr = p.communicate()[1]
    _checkAbort()
    assert p.returncode == 0 and stderr == "",\
      "gzip command returned status code %d, stderr '%s'" % (p.returncode,
      stderr)
  except Exception, e:
    raise _wrapException("error compressing file", e)
  else:
    r.stage = ezidapp.models.DownloadQueue.DELETE
    r.save()
  finally:
    if infile: infile.close()
    if outfile: outfile.close()

def _deleteUncompressedFile (r):
  try:
    if os.path.exists(_path(r, 1)): os.unlink(_path(r, 1))
  except Exception, e:
    raise _wrapException("error deleting uncompressed file", e)
  else:
    r.stage = ezidapp.models.DownloadQueue.MOVE
    r.save()

def _moveCompressedFile (r):
  try:
    if os.path.exists(_path(r, 2)):
      os.rename(_path(r, 2), _path(r, 3))
    else:
      assert os.path.exists(_path(r, 3)), "file has disappeared"
  except Exception, e:
    raise _wrapException("error moving compressed file", e)
  else:
    r.stage = ezidapp.models.DownloadQueue.NOTIFY
    r.save()

def _notifyRequestor (r):
  f = None
  try:
    f = open(_path(r, 4), "w")
    f.write("%s\n%s\n" % (idmap.getAgent(r.requestor)[0],
      r.rawRequest.encode("UTF-8")))
  except Exception, e:
    raise _wrapException("error writing sidecar file", e)
  finally:
    if f: f.close()
  emailAddresses = _decode(r.notify)
  if len(emailAddresses) > 0:
    m = ("The batch download you requested is available at:\n\n" +\
      "%s/download/%s.%s.gz\n\n" +\
      "The download will be deleted in 1 week.\n" +\
      "This is an automated email.  Please do not reply.\n") %\
      (_ezidUrl, r.filename, _suffix[r.format])
    try:
      django.core.mail.send_mail("EZID batch download available", m,
        django.conf.settings.SERVER_EMAIL, emailAddresses, fail_silently=True)
    except Exception, e:
      raise _wrapException("error sending email", e)
  r.delete()

def _daemonThread ():
  doSleep = True
  while True:
    if doSleep: time.sleep(_idleSleep)
    try:
      _checkAbort()
      r = ezidapp.models.DownloadQueue.objects.all().order_by("seq")[:1]
      if len(r) == 0:
        doSleep = True
        continue
      r = r[0]
      _checkAbort()
      if r.stage == ezidapp.models.DownloadQueue.CREATE:
        _createFile(r)
      elif r.stage == ezidapp.models.DownloadQueue.HARVEST:
        _harvest(r)
      elif r.stage == ezidapp.models.DownloadQueue.COMPRESS:
        _compressFile(r)
      elif r.stage == ezidapp.models.DownloadQueue.DELETE:
        _deleteUncompressedFile(r)
      elif r.stage == ezidapp.models.DownloadQueue.MOVE:
        _moveCompressedFile(r)
      elif r.stage == ezidapp.models.DownloadQueue.NOTIFY:
        _notifyRequestor(r)
      else:
        assert False, "unhandled case"
      doSleep = False
    except _AbortException:
      break
    except Exception, e:
      log.otherError("download._daemonThread", e)
      doSleep = True

_loadConfig()
config.addLoader(_loadConfig)
