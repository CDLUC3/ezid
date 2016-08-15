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
import django.db
import logging
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
import search_util
import store
import util

# Deferred imports...
"""
import boto3
"""

_enabled = None
_reportingInterval = None
_threadName = None
_cloudwatchEnabled = None
_cloudwatchRegion = None
_cloudwatchNamespace = None
_cloudwatchInstanceName = None

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
      ndo = datacite.numActiveOperations()
      nstc, nstca = store.numConnections()
      uql = store.getUpdateQueueLength()
      daql = datacite_async.getQueueLength()
      cqs = crossref.getQueueStatistics()
      doql = download.getQueueLength()
      as_ = search_util.numActiveSearches()
      log.status("pid=%d" % os.getpid(),
        "threads=%d" % threading.activeCount(),
        "paused" if isPaused else "running",
        "activeOperations=%d%s" % (na, _formatUserCountList(activeUsers)),
        "waitingRequests=%d%s" % (nw, _formatUserCountList(waitingUsers)),
        "activeDataciteOperations=%d" % ndo,
        "storeDbConnections:active/total=%d/%d" % (nstca, nstc),
        "updateQueueLength=%d" % uql,
        "dataciteQueueLength=%d" % daql,
        "crossrefQueue:archived/unsubmitted/submitted=%d/%d/%d" %\
        (cqs[2]+cqs[3], cqs[0], cqs[1]),
        "downloadQueueLength=%d" % doql,
        "activeSearches=%d" % as_)
      if _cloudwatchEnabled:
        import boto3
        # Disable annoying boto3 logging.
        logging.getLogger("botocore").setLevel(logging.ERROR)
        try:
          c = boto3.client("cloudwatch", region_name=_cloudwatchRegion)
          d = [{ "Name": "InstanceName", "Value": _cloudwatchInstanceName }]
          data = { "ActiveOperations": na, "WaitingRequests": nw,
            "ActiveDataciteOperations": ndo, "UpdateQueueLength": uql,
            "DataciteQueueLength": daql, "CrossrefQueueLength": cqs[0]+cqs[1],
            "DownloadQueueLength": doql, "ActiveSearches": as_ }
          r = c.put_metric_data(Namespace=_cloudwatchNamespace,
            MetricData=[{ "MetricName": k, "Dimensions": d, "Value": float(v),
            "Unit": "Count" } for k, v in data.items()])
          assert type(r) is dict and\
            type(r.get("ResponseMetadata", None)) is dict and\
            r["ResponseMetadata"].get("HTTPStatusCode", None) == 200,\
            "unexpected response: " + util.oneLine(str(r))
        except Exception, e:
          raise Exception("AWS CloudWatch exception: " +\
            util.formatException(e))
    except Exception, e:
      log.otherError("status._statusDaemon", e)
    django.db.connections["default"].close()
    time.sleep(_reportingInterval)

def _loadConfig ():
  global _enabled, _reportingInterval, _threadName, _cloudwatchEnabled
  global _cloudwatchRegion, _cloudwatchNamespace, _cloudwatchInstanceName
  _enabled = django.conf.settings.DAEMON_THREADS_ENABLED and\
    config.get("daemons.status_enabled").lower() == "true"
  if _enabled:
    _reportingInterval = int(config.get("daemons.status_logging_interval"))
    _threadName = uuid.uuid1().hex
    _cloudwatchEnabled = config.get("cloudwatch.enabled").lower() == "true"
    if _cloudwatchEnabled:
      _cloudwatchRegion = config.get("cloudwatch.region")
      _cloudwatchNamespace = config.get("cloudwatch.namespace")
      _cloudwatchInstanceName = config.get("cloudwatch.instance_name")
    t = threading.Thread(target=_statusDaemon, name=_threadName)
    t.setDaemon(True)
    t.start()

_loadConfig()
config.registerReloadListener(_loadConfig)
