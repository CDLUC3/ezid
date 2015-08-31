# =============================================================================
#
# EZID :: datacite_async.py
#
# Asynchronous DataCite processing.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.conf
import random
import threading
import time
import urllib2
import uuid

import config
import datacite
import ezidapp.models
import log
import util

_daemonEnabled = None
_idleSleep = None
_threadName = None
_numWorkerThreads = None
_reattemptDelay = None
_lock = threading.Lock()

class _AbortException (Exception):
  pass

def _checkAbort ():
  # This function provides a handy way to abort processing if the
  # daemon is disabled or if a new daemon thread is started by a
  # configuration reload.  It doesn't entirely eliminate potential
  # race conditions between two daemon threads, but it should make
  # conflicts very unlikely.
  if not _daemonEnabled or\
    not threading.currentThread().getName().startswith(_threadName):
    raise _AbortException()

def _queue ():
  _checkAbort()
  return ezidapp.models.DataciteQueue

# In the following, an in-memory cache of (a portion of) the
# ezidapp_DataciteQueue table, permanent errors and duplicate
# identifiers have been removed.  Rows being processed by a worker
# thread have a 'beingProcessed' attribute added.

_loadedRows = None

def _lockLoadedRows (f):
  # Decorator.
  def wrapped (*args, **kwargs):
    _lock.acquire()
    try:
      _checkAbort()
      return f(*args, **kwargs)
    finally:
      _lock.release()
  return wrapped

@_lockLoadedRows
def _loadedRowsLength ():
  return len(_loadedRows)

@_lockLoadedRows
def _setLoadedRows (rows):
  global _loadedRows
  _loadedRows = rows

@_lockLoadedRows
def _deleteLoadedRow (row):
  for i in range(len(_loadedRows)):
    if _loadedRows[i].seq == row.seq:
      del _loadedRows[i]
      return
  assert False

@_lockLoadedRows
def _nextUnprocessedLoadedRow ():
  for r in _loadedRows:
    if not hasattr(r, "beingProcessed"):
      r.beingProcessed = True
      return r
  return None

def _loadRows (limit=1000):
  qs = _queue().objects.all().order_by("seq")[:limit]
  seen = set()
  rows = []
  for r in qs:
    if r.identifier not in seen and not r.errorIsPermanent: rows.append(r)
    seen.add(r.identifier)
  if len(rows) == 0 and len(qs) == limit:
    # Incredibly unlikely, but just in case: if our query returned a
    # full set of rows but we ended up selecting none (because they
    # all had permanent errors or are duplicates), try increasing the
    # limit.  In the limiting case, the entire table will be returned.
    return _loadRows(limit*2)
  n = len(rows)
  _setLoadedRows(rows)
  return n

def _daemonThread ():
  time.sleep(_idleSleep)
  while True:
    try:
      while True:
        n = _loadRows()
        if n > 0: break
        time.sleep(_idleSleep)
      while _loadedRowsLength() > 0: time.sleep(_idleSleep)
    except _AbortException:
      break
    except Exception, e:
      log.otherError("datacite_async._daemonThread", e)
      time.sleep(_idleSleep)

def _dataciteCallWrapper (row, methodName, function, *args):
  # This function hides all transient errors.  There are three
  # possible returns: True (the function call completed successfully;
  # a transient error might have been recorded in the
  # ezidapp_DataciteQueue database table; 'row' is untouched); or
  # False (a permanent error was encountered, logged, and recorded in
  # the database table; 'row' was removed from _loadedRows); or
  # processing was aborted.
  def formatException (e):
    m = str(e)
    if len(m) > 0: m = ": " + m
    return type(e).__name__ + m
  def permanentError (e):
    row.error = formatException(e)
    row.errorIsPermanent = True
    _checkAbort()
    row.save()
    log.otherError("datacite_async._dataciteCallWrapper/" + methodName, e)
    _deleteLoadedRow(row)
  while True:
    _checkAbort()
    try:
      s = function(*args)
      assert s == None, "error response received from DataCite call: " + s
      return True
    except IOError, e:
      if isinstance(e, urllib2.HTTPError) and e.code < 500:
        permanentError(e)
        return False
      else:
        row.error = formatException(e)
        _checkAbort()
        row.save()
        time.sleep(_reattemptDelay)
    except Exception, e:
      permanentError(e)
      return False

def _workerThread ():
  # Sleep between 1x and 2x the idle sleep, to give the main daemon a
  # chance to load the row cache and to prevent the workers from
  # running synchronously.
  time.sleep(_idleSleep*(random.random()+1))
  while True:
    try:
      while True:
        row = _nextUnprocessedLoadedRow()
        if row != None: break
        time.sleep(_idleSleep)
      doi = row.identifier[4:]
      if row.operation == ezidapp.models.DataciteQueue.OVERWRITE:
        m = util.deblobify(row.metadata)
        if not _dataciteCallWrapper(row, "datacite.uploadMetadata",
          datacite.uploadMetadata, doi, {}, m):
          continue
        if not _dataciteCallWrapper(row, "datacite.setTargetUrl",
          datacite.setTargetUrl, doi, m["_st"]):
          continue
        if m.get("_is", "public") != "public" or\
          m.get("_x", "yes") != "yes":
          if not _dataciteCallWrapper(row, "datacite.deactivate",
            datacite.deactivate, doi):
            continue
      else: # DELETE
        # We can't actually delete a DOI, so we do the next best thing...
        if not _dataciteCallWrapper(row, "datacite.setTargetUrl",
          datacite.setTargetUrl, doi, "http://datacite.org/invalidDOI"):
          continue
        if not _dataciteCallWrapper(row, "datacite.deactivate",
          datacite.deactivate, doi):
          continue
      _checkAbort()
      row.delete()
      _deleteLoadedRow(row)
    except _AbortException:
      break
    except Exception, e:
      log.otherError("datacite_async._workerThread", e)
      time.sleep(_idleSleep)

def enqueueIdentifier (identifier, operation, metadata, blob):
  """
  Adds an identifier to the DataCite asynchronous processing queue.
  'identifier' should be the normalized, qualified identifier, e.g.,
  "doi:10.5060/FOO".  'operation' is the identifier operation as
  reported by the store module.  'metadata' is the identifier's
  metadata dictionary; 'blob' is the same in blob form.
  """
  e = ezidapp.models.DataciteQueue(enqueueTime=int(time.time()),
    identifier=identifier, metadata=blob,
    operation=ezidapp.models.DataciteQueue.operationLabelToCode(operation))
  e.save()

def getQueueLength ():
  """
  Returns the length of the DataCite queue.
  """
  return ezidapp.models.DataciteQueue.objects.count()

def _loadConfig ():
  global _daemonEnabled, _idleSleep, _threadName, _numWorkerThreads
  global _reattemptDelay, _loadedRows
  _lock.acquire()
  try:
    _daemonEnabled = django.conf.settings.DAEMON_THREADS_ENABLED and\
      config.config("daemons.datacite_enabled").lower() == "true"
    _loadedRows = []
    if _daemonEnabled:
      _idleSleep = int(config.config("daemons.datacite_processing_idle_sleep"))
      _threadName = uuid.uuid1().hex
      _numWorkerThreads =\
        int(config.config("daemons.datacite_num_worker_threads"))
      _reattemptDelay =\
        int(config.config("daemons.datacite_processing_error_sleep"))
      t = threading.Thread(target=_daemonThread, name=_threadName)
      t.setDaemon(True)
      t.start()
      for i in range(_numWorkerThreads):
        t = threading.Thread(target=_workerThread,
          name="%s.%d" % (_threadName, i))
        t.setDaemon(True)
        t.start()
  finally:
    _lock.release()

_loadConfig()
config.addLoader(_loadConfig)
