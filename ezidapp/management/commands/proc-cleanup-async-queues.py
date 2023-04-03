#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Clean up entries that are successfully completed or are a 'no-op'

Identifier operation entries are retrieved by querying the database;
operations that successfully completed or are a no-op are deleted based on
pre-set interval.

Iden
"""

import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.response

import django.conf
import django.conf
import django.db
import django.db.transaction

import ezidapp.management.commands.proc_base
import ezidapp.models.identifier
import ezidapp.models.identifier
import ezidapp.models.news_feed
import ezidapp.models.shoulder
from django.db.models import Q

import impl.enqueue
import impl.ezid

log = logging.getLogger(__name__)


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    name = __name__
    # TODO: set up flag in J2 template
    setting = 'DAEMONS_QUEUE_CLEANUP_ENABLED'
    queueType = {
        'binder': ezidapp.models.async_queue.BinderQueue,
        'crossref': ezidapp.models.async_queue.CrossrefQueue,
        'datacite': ezidapp.models.async_queue.DataciteQueue,
        'search': ezidapp.models.async_queue.SearchIndexerQueue
    }
    refIdentifier = ezidapp.models.identifier.RefIdentifier

    def __init__(self):
        super().__init__()

    def run(self):
        keepRunning = True
        while keepRunning:
            for key, value in self.queueType.items():
                log.info("Running job for " + key)
                queue = value

                qs = queue.objects.filter(
                    Q(status=queue.SUCCESS)
                    | Q(status=queue.IGNORED)
                ).order_by("seq")[: django.conf.settings.DAEMONS_MAX_BATCH_SIZE]

                if not qs:
                    self.sleep(django.conf.settings.DAEMONS_IDLE_SLEEP)
                    continue

                for task_model in qs:
                    log.info('-' * 100)
                    log.info(f'Processing task: {str(task_model)}')
                    self.deleteRecord(queue, task_model)

            keepRunning=False

            # TODO: set up flag in J2 template
            self.sleep(django.conf.settings.DAEMONS_BATCH_SLEEP)

    def deleteRecord(self, queue, task_model):
        try:
            queue.objects.filter(seq=task_model.pk).delete()
        except Exception as e:
            log.error(e)
