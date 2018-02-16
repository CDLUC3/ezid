# =============================================================================
#
# EZID :: register_async.py
#
# Generic support for asynchronous identifier registration with
# external registrars.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2017, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.db
import httplib
import random
import threading
import time
import urllib2

import ezidapp.models
import log
import util

class _StateHolder (object):
  def __init__ (self, registrar, queueModel, createFunction, updateFunction,
    deleteFunction, idleSleep, reattemptDelay, enabledFlagHolder,
    threadNameHolder):
    # Configuration variables.
    self.registrar = registrar
    self.queueModel = queueModel
    self.createFunction = createFunction
    self.updateFunction = updateFunction
    self.deleteFunction = deleteFunction
    self.idleSleep = idleSleep
    self.reattemptDelay = reattemptDelay
    self.enabledFlagHolder = enabledFlagHolder
    self.threadNameHolder = threadNameHolder
    # State variables.  'loadedRows' is an in-memory cache of (a
    # portion of) the queue table; permanent errors and duplicate
    # identifiers have been removed.  Rows being actively processed by
    # a worker thread have a 'beingProcessed' attribute added.
    self.loadedRows = []
    self.lock = threading.Lock()

class _AbortException (Exception):
  pass

def _checkAbort (sh):
  # This function provides a handy way to abort processing if daemons
  # are disabled or if a new daemon thread is started by a
  # configuration reload.  It doesn't entirely eliminate potential
  # race conditions between two daemon threads (for the same
  # registrar), but it should make conflicts very unlikely.
  if not sh.enabledFlagHolder[0] or\
    not threading.currentThread().getName().startswith(
    sh.threadNameHolder[0]):
    raise _AbortException()

def _queue (sh):
  _checkAbort(sh)
  return sh.queueModel

def _lockLoadedRows (f):
  # Decorator.  Assumes the state holder is the first argument to the
  # decorated function.
  def wrapped (*args, **kwargs):
    sh = args[0]
    sh.lock.acquire()
    try:
      _checkAbort(sh)
      return f(*args, **kwargs)
    finally:
      sh.lock.release()
  return wrapped

@_lockLoadedRows
def _loadedRowsLength (sh):
  return len(sh.loadedRows)

@_lockLoadedRows
def _setLoadedRows (sh, rows):
  sh.loadedRows = rows

@_lockLoadedRows
def _deleteLoadedRow (sh, row):
  for i in range(len(sh.loadedRows)):
    if sh.loadedRows[i].seq == row.seq:
      del sh.loadedRows[i]
      return
  assert False, "row to be deleted not found"

@_lockLoadedRows
def _nextUnprocessedLoadedRow (sh):
  for r in sh.loadedRows:
    if not hasattr(r, "beingProcessed"):
      r.beingProcessed = True
      return r
  return None

def _loadRows (sh, limit=1000):
  qs = _queue(sh).objects.all().order_by("seq")[:limit]
  seen = set()
  rows = []
  for r in qs:
    if r.identifier not in seen:
      if not r.errorIsPermanent: rows.append(r)
      seen.add(r.identifier)
  if len(rows) == 0 and len(qs) == limit:
    # Incredibly unlikely, but just in case: if our query returned a
    # full set of rows but we ended up selecting none (because they
    # all had permanent errors or are duplicates), try increasing the
    # limit.  In the limiting case, the entire table will be returned.
    return _loadRows(sh, limit*2)
  n = len(rows)
  _setLoadedRows(sh, rows)
  return n

def _sleep (sh, duration=None):
  django.db.connections["default"].close()
  time.sleep(duration or sh.idleSleep)

def _daemonThread (sh):
  _sleep(sh)
  while True:
    try:
      while True:
        n = _loadRows(sh)
        if n > 0: break
        _sleep(sh)
      while _loadedRowsLength(sh) > 0: _sleep(sh)
    except _AbortException:
      break
    except Exception, e:
      log.otherError("register_async._daemonThread/" + sh.registrar, e)
      _sleep(sh)

def callWrapper (sh, row, methodName, function, *args):
  """
  This function should be used by registrars to wrap calls to
  registrar-specific create/update/delete functions.  It hides all
  transient errors (by retrying indefinitely) and raises all others.
  'sh' and 'row' are supplied by this module and should simply be
  passed through.  'function' is the function to call; 'methodName' is
  its name for error reporting purposes.  Any additional arguments are
  passed through to 'function'.
  """
  while True:
    _checkAbort(sh)
    try:
      return function(*args)
    except Exception, e:
      if (isinstance(e, urllib2.HTTPError) and e.code >= 500) or\
        (isinstance(e, IOError) and not isinstance(e, urllib2.HTTPError)) or\
        isinstance(e, httplib.HTTPException):
        row.error = util.formatException(e)
        _checkAbort(sh)
        row.save()
        _sleep(sh, sh.reattemptDelay)
      else:
        raise Exception("%s error: %s" % (methodName, util.formatException(e)))

def _workerThread (sh):
  # Sleep between 1x and 2x the idle sleep, to give the main daemon a
  # chance to load the row cache and to prevent the workers from
  # running synchronously.
  time.sleep(sh.idleSleep*(random.random()+1))
  while True:
    try:
      while True:
        row = _nextUnprocessedLoadedRow(sh)
        if row != None: break
        _sleep(sh)
      try:
        if row.operation == ezidapp.models.RegistrationQueue.CREATE:
          f = sh.createFunction
        elif row.operation == ezidapp.models.RegistrationQueue.UPDATE:
          f = sh.updateFunction
        elif row.operation == ezidapp.models.RegistrationQueue.DELETE:
          f = sh.deleteFunction
        else:
          assert False, "unhandled case"
        f(sh, row, row.identifier, util.deblobify(row.metadata))
      except _AbortException:
        raise
      except Exception, e:
        # N.B.: on the assumption that the registrar-specific function
        # used callWrapper defined above, the error can only be
        # permanent.
        row.error = util.formatException(e)
        row.errorIsPermanent = True
        _checkAbort(sh)
        row.save()
        log.otherError("register_async._workerThread/" + sh.registrar, e)
      else:
        _checkAbort(sh)
        row.delete()
      finally:
        _deleteLoadedRow(sh, row)
    except _AbortException:
      break
    except Exception, e:
      log.otherError("register_async._workerThread/" + sh.registrar, e)
      _sleep(sh)

def enqueueIdentifier (model, identifier, operation, blob):
  """
  Adds an identifier to the asynchronous registration queue named by
  'model'.  'identifier' should be the normalized, qualified
  identifier, e.g., "doi:10.5060/FOO".  'operation' is the identifier
  operation and should be one of the strings "create", "update", or
  "delete".  'blob' is the identifier's metadata dictionary in blob
  form.
  """
  e = model(enqueueTime=int(time.time()), identifier=identifier, metadata=blob,
    operation=ezidapp.models.RegistrationQueue.operationLabelToCode(operation))
  e.save()

def launch (registrar, queueModel, createFunction, updateFunction,
  deleteFunction, numWorkerThreads, idleSleep, reattemptDelay,
  enabledFlagHolder, threadNameHolder):
  """
  Launches a registration thread (and subservient worker threads).
  'registrar' is the registrar the thread is for, e.g., "datacite".
  'queueModel' is the registrar's queue database model, e.g.,
  ezidapp.models.DataciteQueue.  'createFunction', 'updateFunction',
  and 'deleteFunction' are the registrar-specific functions to be
  called.  Each should accept arguments (sh, row, identifier,
  metadata) where 'identifier' is a normalized, qualified identifier,
  e.g., "doi:10.5060/FOO", and 'metadata' is the identifier's metadata
  dictionary.  Each function should wrap external HTTP calls using
  'callWrapper' above, passing through the 'sh' and 'row' arguments.
  'enabledFlagHolder' is a singleton list containing a boolean flag
  that indicates if the thread is enabled.  'threadNameHolder' is a
  singleton list containing the string name of the current thread.
  """
  sh = _StateHolder(registrar, queueModel, createFunction, updateFunction,
    deleteFunction, idleSleep, reattemptDelay, enabledFlagHolder,
    threadNameHolder)
  name = threadNameHolder[0]
  t = threading.Thread(target=lambda: _daemonThread(sh), name=name)
  t.setDaemon(True)
  t.start()
  for i in range(numWorkerThreads):
    t = threading.Thread(target=lambda: _workerThread(sh),
      name="%s.%d" % (name, i))
    t.setDaemon(True)
    t.start()
