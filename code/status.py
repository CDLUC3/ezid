# =============================================================================
#
# EZID :: status.py
#
# Periodic status reporting.
#
# This module should be imported at server startup so that its daemon
# thread is started.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2013, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.conf
import os
import threading
import time
import uuid

import config
import datacite
import ezid
import log
import search
import store

_enabled = None
_reportingInterval = None
_threadName = None

def _formatUserCountList (d):
  if len(d) > 0:
    l = d.items()
    l.sort(cmp=lambda x, y: -cmp(x[1], y[1]))
    return " (" + " ".join("%s=%d" % i for i in l) + ")"
  else:
    return ""

def _statusDaemon ():
  while _enabled and threading.currentThread().getName() == _threadName:
    try:
      activeUsers, waitingUsers, isPaused = ezid.getStatus()
      na = sum(activeUsers.values())
      nw = sum(waitingUsers.values())
      nstc, nstca = store.numConnections()
      nsec, nseca = search.numConnections()
      log.status("pid=%d" % os.getpid(),
        "threads=%d" % threading.activeCount(),
        "paused" if isPaused else "running",
        "activeOperations=%d%s" % (na, _formatUserCountList(activeUsers)),
        "waitingRequests=%d%s" % (nw, _formatUserCountList(waitingUsers)),
        "activeDataciteOperations=%d" % datacite.numActiveOperations(),
        "active/totalStoreDatabaseConnections=%d/%d" % (nstca, nstc),
        "active/totalSearchDatabaseConnections=%d/%d" % (nseca, nsec),
        "updateQueueLength=%d" % store.getUpdateQueueLength())
    except Exception, e:
      log.otherError("status._statusDaemon", e)
    time.sleep(_reportingInterval)

def _loadConfig ():
  global _enabled, _reportingInterval, _threadName
  _enabled = django.conf.settings.DAEMON_THREADS_ENABLED
  if _enabled:
    _reportingInterval = int(config.config("DEFAULT.status_logging_interval"))
    _threadName = uuid.uuid1().hex
    t = threading.Thread(target=_statusDaemon, name=_threadName)
    t.setDaemon(True)
    t.start()

_loadConfig()
config.addLoader(_loadConfig)
