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
import crossref
import datacite
import datacite_async
import download
import ezid
import log
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
      cqs = crossref.getQueueStatistics()
      log.status("pid=%d" % os.getpid(),
        "threads=%d" % threading.activeCount(),
        "paused" if isPaused else "running",
        "activeOperations=%d%s" % (na, _formatUserCountList(activeUsers)),
        "waitingRequests=%d%s" % (nw, _formatUserCountList(waitingUsers)),
        "activeDataciteOperations=%d" % datacite.numActiveOperations(),
        "storeDbConnections:active/total=%d/%d" % (nstca, nstc),
        "updateQueueLength=%d" % store.getUpdateQueueLength(),
        "dataciteQueueLength=%d" % datacite_async.getQueueLength(),
        "crossrefQueue:archived/unsubmitted/submitted=%d/%d/%d" %\
        (cqs[2]+cqs[3], cqs[0], cqs[1]),
        "downloadQueueLength=%d" % download.getQueueLength())
    except Exception, e:
      log.otherError("status._statusDaemon", e)
    time.sleep(_reportingInterval)

def _loadConfig ():
  global _enabled, _reportingInterval, _threadName
  _enabled = django.conf.settings.DAEMON_THREADS_ENABLED and\
    config.get("daemons.status_enabled").lower() == "true"
  if _enabled:
    _reportingInterval = int(config.get("daemons.status_logging_interval"))
    _threadName = uuid.uuid1().hex
    t = threading.Thread(target=_statusDaemon, name=_threadName)
    t.setDaemon(True)
    t.start()

_loadConfig()
config.registerReloadListener(_loadConfig)
