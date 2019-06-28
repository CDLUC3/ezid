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
import django.db.transaction
import threading
import time
import uuid

import binder_async
import config
import crossref
import datacite_async
import ezidapp.models
import ezidapp.models.search_identifier
import log
import search_util
import util

_enabled = None
_lock = threading.Lock()
_runningThreads = set()
_threadName = None
_idleSleep = None

def _updateSearchDatabase (identifier, operation, metadata, blob):
  if operation in ["create", "update"]:
    ezidapp.models.search_identifier.updateFromLegacy(identifier, metadata)
  elif operation == "delete":
    ezidapp.models.SearchIdentifier.objects.filter(identifier=identifier).\
      delete()
  else:
    assert False, "unrecognized operation"

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
      l = list(ezidapp.models.UpdateQueue.objects.all().order_by("seq")[:1000])
      if len(l) > 0:
        for uq in l:
          if not _checkContinue(): break
          # The use of legacy representations and blobs will go away soon.
          metadata = uq.actualObject.toLegacy()
          blob = util.blobify(metadata)
          if uq.actualObject.owner != None:
            try:
              search_util.withAutoReconnect("backproc._updateSearchDatabase",
                lambda: _updateSearchDatabase(uq.identifier,
                uq.get_operation_display(), metadata, blob), _checkContinue)
            except search_util.AbortException:
              break
          with django.db.transaction.atomic():
            if not uq.actualObject.isReserved:
              binder_async.enqueueIdentifier(uq.identifier,
                uq.get_operation_display(), blob)
              if uq.updateExternalServices:
                if uq.actualObject.isDatacite:
                  if not uq.actualObject.isTest:
                    datacite_async.enqueueIdentifier(uq.identifier,
                      uq.get_operation_display(), blob)
                elif uq.actualObject.isCrossref:
                  crossref.enqueueIdentifier(uq.identifier,
                    uq.get_operation_display(), metadata, blob)
            uq.delete()
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
