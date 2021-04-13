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

import impl.daemon.daemon_base
import logging
import os
import threading
import time
import uuid

import boto3
import django.conf
import django.db

import ezidapp.models.update_queue
import impl.daemon.binder
import impl.daemon.crossref
import impl.datacite
import impl.daemon.datacite
import impl.daemon.download
import impl.ezid
import impl.log
import impl.search_util


class StatusDaemon(impl.daemon.daemon_base.DaemonBase):
    def __init__(self):
        super(StatusDaemon, self).__init__()

    def _formatUserCountList(self, d):
        if len(d) > 0:
            l = list(d.items())
            l.sort(key=lambda x: -x[1])
            return " (" + " ".join("{}={:d}".format(x[0], x[1]) for x in l) + ")"
        else:
            return ""

    def _statusDaemon(
        self,
    ):
        while (
            django.conf.settings.CROSSREF_ENABLED
            and threading.currentThread().getName() == _threadName
        ):
            try:
                activeUsers, waitingUsers, isPaused = impl.ezid.getStatus()
                na = sum(activeUsers.values())
                nw = sum(waitingUsers.values())
                ndo = impl.datacite.numActiveOperations()
                uql = ezidapp.models.update_queue.UpdateQueue.objects.count()
                bql = impl.daemon.binder.getQueueLength()
                daql = impl.daemon.datacite.getQueueLength()
                cqs = impl.daemon.crossref.getQueueStatistics()
                doql = impl.daemon.download.getQueueLength()
                as_ = impl.search_util.numActiveSearches()
                no = impl.log.getOperationCount()
                impl.log.resetOperationCount()
                impl.log.status(
                    f"pid={os.getpid():d}",
                    f"threads={threading.activeCount():d}",
                    "paused" if isPaused else "running",
                    f"activeOperations={na:d}{_formatUserCountList(activeUsers)}",
                    f"waitingRequests={nw:d}{_formatUserCountList(waitingUsers)}",
                    f"activeDataciteOperations={ndo:d}",
                    f"updateQueueLength={uql:d}",
                    f"binderQueueLength={bql:d}",
                    f"dataciteQueueLength={daql:d}",
                    f"crossrefQueue:archived/unsubmitted/submitted={cqs[2] + cqs[3]:d}/{cqs[0]:d}/{cqs[1]:d}",
                    f"downloadQueueLength={doql:d}",
                    f"activeSearches={as_:d}",
                    f"operationCount={no:d}",
                )
                if _cloudwatchEnabled:
                    # Disable annoying boto3 logging.
                    logging.getLogger("botocore").setLevel(logging.ERROR)
                    try:
                        c = boto3.client("cloudwatch", region_name=_cloudwatchRegion)
                        d = [{"Name": "InstanceName", "Value": _cloudwatchInstanceName}]
                        # noinspection PyTypeChecker
                        data = {
                            "ActiveOperations": na,
                            "WaitingRequests": nw,
                            "ActiveDataciteOperations": ndo,
                            "UpdateQueueLength": uql,
                            "BinderQueueLength": bql,
                            "DataciteQueueLength": daql,
                            "CrossrefQueueLength": cqs[0] + cqs[1],
                            "DownloadQueueLength": doql,
                            "ActiveSearches": as_,
                            "OperationRate": float(no) / _reportingInterval,
                        }
                        r = c.put_metric_data(
                            Namespace=_cloudwatchNamespace,
                            MetricData=[
                                {
                                    "MetricName": k,
                                    "Dimensions": d,
                                    "Value": float(v),
                                    "Unit": "Count/Second"
                                    if k == "OperationRate"
                                    else "Count",
                                }
                                for k, v in list(data.items())
                            ],
                        )
                        assert r["ResponseMetadata"]["HTTPStatusCode"] == 200
                    except Exception:
                        # Ignore CloudWatch exceptions, as it's not essential.
                        pass
            except Exception as e:
                impl.log.otherError("status._statusDaemon", e)
            django.db.connections["default"].close()
            # noinspection PyTypeChecker
            time.sleep(_reportingInterval)

    _threadName = None

    _cloudwatchRegion = None
    _cloudwatchNamespace = None
    _cloudwatchInstanceName = None

    _cloudwatchEnabled = None
    _reportingInterval = None
    django.conf.settings.CROSSREF_ENABLED = (
        django.conf.settings.DAEMON_THREADS_ENABLED
        and django.conf.settings.DAEMONS_STATUS_ENABLED
    )
    if django.conf.settings.CROSSREF_ENABLED:
        _reportingInterval = int(django.conf.settings.DAEMONS_STATUS_LOGGING_INTERVAL)
        _threadName = uuid.uuid1().hex
        _cloudwatchEnabled = django.conf.settings.CLOUDWATCH_ENABLED
        if _cloudwatchEnabled:
            _cloudwatchRegion = django.conf.settings.CLOUDWATCH_REGION
            _cloudwatchNamespace = django.conf.settings.CLOUDWATCH_NAMESPACE
            _cloudwatchInstanceName = django.conf.settings.CLOUDWATCH_INSTANCE_NAME
        t = threading.Thread(target=_statusDaemon, name=_threadName)
        t.setDaemon(True)
        t.start()
