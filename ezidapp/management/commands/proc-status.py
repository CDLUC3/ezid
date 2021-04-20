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
import logging
import os
import threading
import time
import types

import boto3
import django.conf
import django.core.management
import django.db

import ezidapp.management.commands.proc_base
import ezidapp.models.update_queue
import impl.datacite
import impl.ezid
import impl.log
import impl.nog.util
import impl.search_util
import impl.statistics

log = logging.getLogger(__name__)


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    name = 'Status'
    setting = 'DAEMONS_STATISTICS_ENABLED'

    def __init__(self):
        super(Command, self).__init__(__name__)
        # Disable annoying boto3 logging.
        logging.getLogger("botocore").setLevel(logging.ERROR)

    def add_arguments(self, parser):
        super().add_arguments(parser)

    def handle_daemon(self, args):
        while True:
            try:
                status = self.collect_status()
            except Exception as e:
                impl.log.otherError("status._statusDaemon", e)
            else:
                if django.conf.settings.CLOUDWATCH_ENABLED:
                    try:
                        self.updateCloudwatch(status)
                    except Exception as e:
                        log.error(f'Cloudwatch update failed. error="{status}"')
                        if self.is_debug:
                            raise

            django.db.connections["default"].close()
            time.sleep(django.conf.settings.DAEMONS_STATUS_LOGGING_INTERVAL)

    def collect_status(self):
        activeUsers, waitingUsers, isPaused = impl.ezid.getStatus()
        stat_dict = dict(
            activeUsers=activeUsers,
            waitingUsers=waitingUsers,
            isPaused=isPaused,
            na=sum(activeUsers.values()),
            nw=sum(waitingUsers.values()),
            ndo=impl.datacite.numActiveOperations(),
            uql=impl.statistics.getUpdateQueueLength(),
            bql=impl.statistics.getBinderQueueLength(),
            daql=impl.statistics.getDataCiteQueueLength(),
            cqs=impl.statistics.getCrossRefQueueStatistics(),
            doql=impl.statistics.getDownloadQueueLength(),
            as_=impl.search_util.numActiveSearches(),
            no=impl.log.getOperationCount(),
        )
        impl.log.resetOperationCount()
        status = types.SimpleNamespace(**stat_dict)
        self.log_status(activeUsers, isPaused, status, waitingUsers)

        return status

    def log_status(self, activeUsers, isPaused, status, waitingUsers):
        impl.log.status(
            f"pid={os.getpid():d}",
            f"threads={threading.activeCount():d}",
            "paused" if isPaused else "running",
            f"activeOperations={status.na:d}{self._formatUserCountList(activeUsers)}",
            f"waitingRequests={status.nw:d}{self._formatUserCountList(waitingUsers)}",
            f"activeDataciteOperations={status.ndo:d}",
            f"updateQueueLength={status.uql:d}",
            f"binderQueueLength={status.bql:d}",
            f"dataciteQueueLength={status.daql:d}",
            f"crossrefQueue:archived/unsubmitted/submitted={status.cqs[2] + status.cqs[3]:d}/{status.cqs[0]:d}/{status.cqs[1]:d}",
            f"downloadQueueLength={status.doql:d}",
            f"activeSearches={status.as_:d}",
            f"operationCount={status.no:d}",
        )

    def updateCloudwatch(self, status):
        c = boto3.client("cloudwatch", region_name=self._cloudwatchRegion)
        d = [
            {
                "Name": "InstanceName",
                "Value": self._cloudwatchInstanceName,
            }
        ]
        # noinspection PyTypeChecker
        data = {
            "ActiveOperations": status.na,
            "WaitingRequests": status.nw,
            "ActiveDataciteOperations": status.ndo,
            "UpdateQueueLength": status.uql,
            "BinderQueueLength": status.bql,
            "DataciteQueueLength": status.daql,
            "CrossrefQueueLength": status.cqs[0] + status.cqs[1],
            "DownloadQueueLength": status.doql,
            "ActiveSearches": status.as_,
            "OperationRate": float(status.no)
            / django.conf.settings.DAEMONS_STATUS_LOGGING_INTERVAL,
        }
        r = c.put_metric_data(
            Namespace=self._cloudwatchNamespace,
            MetricData=[
                {
                    "MetricName": k,
                    "Dimensions": d,
                    "Value": float(v),
                    "Unit": "Count/Second" if k == "OperationRate" else "Count",
                }
                for k, v in list(data.items())
            ],
        )
        assert r["ResponseMetadata"]["HTTPStatusCode"] == 200

    def _formatUserCountList(self, d):
        if len(d) > 0:
            l = list(d.items())
            l.sort(key=lambda x: -x[1])
            return " (" + " ".join("{}={:d}".format(x[0], x[1]) for x in l) + ")"
        else:
            return ""
