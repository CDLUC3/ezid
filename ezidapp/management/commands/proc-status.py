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
import impl.datacite
import impl.ezid
import impl.log
import impl.nog.util
import impl.search_util
import impl.statistics

log = logging.getLogger(__name__)


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    display = 'Status'
    name = 'status'
    setting = 'DAEMONS_STATISTICS_ENABLED'

    def __init__(self):
        super(Command, self).__init__(__name__)

    def add_arguments(self, parser):
        super().add_arguments(parser)

    def handle_daemon(self, args):
        while True:
            try:
                status_sn = self.collect_status()
                self.log_status(status_sn)
                impl.log.resetOperationCount()
            except Exception as e:
                log.exception(' Exception as e')
                self.otherError(self.name, e)
            else:
                if django.conf.settings.CLOUDWATCH_ENABLED:
                    try:
                        self.updateCloudwatch(status_sn)
                    except Exception as e:
                        log.exception(' Exception as e')
                        log.error(f'Cloudwatch update failed. error="{repr(e)}"')
                        if self.is_debug:
                            raise

            django.db.connections["default"].close()
            time.sleep(django.conf.settings.DAEMONS_STATUS_LOGGING_INTERVAL)

    def collect_status(self):
        activeUsers, waitingUsers, isPaused = impl.ezid.getStatus()
        status_sn = types.SimpleNamespace(
            pid=os.getpid(),
            threadId=threading.get_native_id(),
            numThreads=threading.activeCount(),
            paused='paused' if isPaused else "running",
            activeUsers=self._formatUserCountList(activeUsers),
            waitingUsers=self._formatUserCountList(waitingUsers),
            isPaused=isPaused,
            numActiveUsers=sum(activeUsers.values()),
            numWaitingUsers=sum(waitingUsers.values()),
            numActiveOperations=impl.datacite.numActiveOperations(),
            binderQueueLength=impl.statistics.getBinderQueueLength(),
            dataCiteQueueLength=impl.statistics.getDataCiteQueueLength(),
            crossrefQueueStatistics=impl.statistics.getCrossrefQueueStatistics(),
            downloadQueueLength=impl.statistics.getDownloadQueueLength(),
            numActiveSearches=impl.search_util.numActiveSearches(),
            operationCount=impl.log.getOperationCount(),
        )
        return status_sn

    def log_status(self, status_sn: types.SimpleNamespace):
        xd = status_sn.crossrefQueueStatistics
        d = {
            **vars(status_sn),
            **{
                'getCrossrefQueueStatistics': 'crossrefQueue:archived/unsubmitted/submitted={}/{}/{}'.format(
                    xd.registered_with_warning + xd.registration_failed,
                    xd.awaiting_submission,
                    xd.submitted,
                ),
            },
        }

        log.info("STATUS " + ' '.join(f'{k}={v}' for k, v in vars(status_sn).items()))
        # impl.log.status(
        #     f"pid={os.getpid()}",
        #     f"threads={threading.activeCount()}",
        #     "paused" if isPaused else "running",
        #     f"activeOperations={status.numActiveUsers}",
        #     f"waitingRequests={status.numWaitingUsers}",
        #     f"activeDataciteOperations={status.numActiveOperations}",
        #     f"updateQueueLength={status.updateQueueLength}",
        #     f"binderQueueLength={status.binderQueueLength}",
        #     f"dataciteQueueLength={status.dataCiteQueueLength}",
        #     'crossrefQueue:archived/unsubmitted/submitted={}/{}/{}'.format(
        #         (status.registered_with_warning + status.registration_failed), status.awaiting_submission, status.submitted
        #     ),
        #     f"downloadQueueLength={status.downloadQueueLength}",
        #     f"activeSearches={status.numActiveSearches}",
        #     f"operationCount={status.operationCount}",
        # )

    def updateCloudwatch(self, status_sn):
        client = boto3.client("cloudwatch", region_name=django.conf.settings.CLOUDWATCH_REGION)
        # noinspection PyTypeChecker
        xd = status_sn.crossrefQueueStatistics
        cloud_dict = {
            "ActiveOperations": status_sn.numActiveUsers,
            "WaitingRequests": status_sn.numWaitingUsers,
            "ActiveDataciteOperations": status_sn.numActiveOperations,
            "BinderQueueLength": status_sn.binderQueueLength,
            "DataciteQueueLength": status_sn.dataCiteQueueLength,
            "CrossrefQueueLength": xd.awaiting_submission + xd.submitted,
            "DownloadQueueLength": status_sn.downloadQueueLength,
            "ActiveSearches": status_sn.numActiveSearches,
            "OperationRate": float(status_sn.operationCount) / django.conf.settings.DAEMONS_STATUS_LOGGING_INTERVAL,
        }
        response = client.put_metric_data(
            Namespace=django.conf.settings.CLOUDWATCH_NAMESPACE,
            MetricData=[
                {
                    "MetricName": k,
                    "Dimensions": [
                        {
                            "Name": "InstanceName",
                            "Value": django.conf.settings.CLOUDWATCH_INSTANCE_NAME,
                        }
                    ],
                    "Value": float(v),
                    "Unit": "Count/Second" if k == "OperationRate" else "Count",
                }
                for k, v in cloud_dict.items()
            ],
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    def _formatUserCountList(self, d):
        if len(d) > 0:
            l = list(d.items())
            l.sort(key=lambda x: -x[1])
            return " (" + " ".join("{}={}".format(x[0], x[1]) for x in l) + ")"
        else:
            return "0"
