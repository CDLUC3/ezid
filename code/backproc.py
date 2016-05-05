# =============================================================================
#
# EZID :: backproc.py
#
# Background identifier processing.
#
# This module should be imported at server startup so that its daemon
# thread is started.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2014, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.conf
import django.db
import threading
import time
import uuid

import config
import crossref
import datacite_async
import ezidapp.models
import ezidapp.models.search_identifier
import log
import search_util
import store

_enabled = None
_lock = threading.Lock()
_runningThreads = set()
_threadName = None
_idleSleep = None

def _updateSearchDatabase (identifier, operation, metadata, blob):
  if metadata["_o"] == "anonymous": return
  if "_s" in metadata:
    identifier = metadata["_s"]
  else:
    identifier = "ark:/" + identifier
  if operation in ["create", "modify"]:
    ezidapp.models.search_identifier.updateFromLegacy(identifier, metadata)
  elif operation == "delete":
    ezidapp.models.SearchIdentifier.objects.filter(identifier=identifier).\
      delete()
  else:
    assert False, "unrecognized operation"

def _updateDataciteQueue (identifier, operation, metadata, blob):
  if "_s" in metadata and metadata["_s"].startswith("doi:") and\
    metadata.get("_is", "public") != "reserved":
    datacite_async.enqueueIdentifier(metadata["_s"], operation, metadata, blob)

def _updateCrossrefQueue (identifier, operation, metadata, blob):
  if "_cr" not in metadata: return
  if metadata.get("_is", "public") == "reserved": return
  assert "_s" in metadata and metadata["_s"].startswith("doi:")
  crossref.enqueueIdentifier(metadata["_s"], operation, metadata, blob)

def _checkContinue ():
  return _enabled and threading.currentThread().getName() == _threadName

def _backprocDaemon ():
  _lock.acquire()
  try:
    _runningThreads.add(threading.currentThread().getName())
  finally:
    _lock.release()
  # If we were started due to a reload, we wait for the previous
  # thread to terminate... but not forever.  60 seconds is arbitrary.
  totalWaitTime = 0
  try:
    while _checkContinue():
      _lock.acquire()
      try:
        n = len(_runningThreads)
      finally:
        _lock.release()
      if n == 1: break
      assert totalWaitTime <= 60,\
        "new backproc daemon started before previous daemon terminated"
      totalWaitTime += _idleSleep
      time.sleep(_idleSleep)
  except AssertionError, e:
    log.otherError("backproc._backprocDaemon", e)
  # Regular processing.
  while _checkContinue():
    try:
      l = store.getUpdateQueue(maximum=1000)
      if len(l) > 0:
        for seq, identifier, metadata, blob, operation in l:
          if not _checkContinue(): break
          # The following four statements form a kind of atomic
          # transaction.  Hence, if the first statement succeeds, we
          # proceed straight through with no intervening continuation
          # checks.
          try:
            search_util.withAutoReconnect("backproc._updateSearchDatabase",
              lambda: _updateSearchDatabase(identifier, operation,
              metadata, blob), _checkContinue)
          except search_util.AbortException:
            break
          _updateDataciteQueue(identifier, operation, metadata, blob)
          _updateCrossrefQueue(identifier, operation, metadata, blob)
          store.deleteFromUpdateQueue(seq)
      else:
        django.db.connections["default"].close()
        django.db.connections["search"].close()
        time.sleep(_idleSleep)
    except Exception, e:
      log.otherError("backproc._backprocDaemon", e)
      django.db.connections["default"].close()
      django.db.connections["search"].close()
      time.sleep(_idleSleep)
  _lock.acquire()
  try:
    _runningThreads.remove(threading.currentThread().getName())
  finally:
    _lock.release()

def _loadConfig ():
  global _enabled, _idleSleep, _threadName
  _enabled = django.conf.settings.DAEMON_THREADS_ENABLED and\
    config.get("daemons.backproc_enabled").lower() == "true"
  if _enabled:
    _idleSleep = int(config.get("daemons.background_processing_idle_sleep"))
    _threadName = uuid.uuid1().hex
    t = threading.Thread(target=_backprocDaemon, name=_threadName)
    t.setDaemon(True)
    t.start()

_loadConfig()
config.registerReloadListener(_loadConfig)
