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
import threading
import time
import uuid

import config
import log
import search
import store

_enabled = None
_threadName = None
_idleSleep = None

def _updateSearchDatabase (identifier, operation, metadata):
  if metadata["_o"] == "anonymous": return
  if "_s" in metadata:
    identifier = metadata["_s"]
  else:
    identifier = "ark:/" + identifier
  if operation == "create":
    search.insert(identifier, metadata)
  elif operation == "modify":
    search.update(identifier, metadata)
  elif operation == "delete":
    search.delete(identifier)
  else:
    assert False, "unrecognized operation"

def _backprocDaemon ():
  while _enabled and threading.currentThread().getName() == _threadName:
    try:
      l = store.getUpdateQueue(maximum=1000)
      if len(l) > 0:
        for seq, identifier, metadata, operation in l:
          if not _enabled or\
            threading.currentThread().getName() != _threadName:
            break
          _updateSearchDatabase(identifier, operation, metadata)
          store.deleteFromUpdateQueue(seq)
      else:
        time.sleep(_idleSleep)
    except Exception, e:
      log.otherError("backproc._backprocDaemon", e)

def _loadConfig ():
  global _enabled, _idleSleep, _threadName
  _enabled = django.conf.settings.DAEMON_THREADS_ENABLED and\
    config.config("daemons.backproc_enabled").lower() == "true"
  if _enabled:
    _idleSleep = int(config.config("daemons.background_processing_idle_sleep"))
    _threadName = uuid.uuid1().hex
    t = threading.Thread(target=_backprocDaemon, name=_threadName)
    t.setDaemon(True)
    t.start()

_loadConfig()
config.addLoader(_loadConfig)
