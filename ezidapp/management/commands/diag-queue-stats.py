#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Report queue statuses

For each queue, report the number of entries at each status level.

For queues other than download:
  U = Unsubmitted
  C = Unchecked
  S = Submitted
  W = Warning
  F = Failure
  I = Ignored
  O = Success
"""

import json
import logging

import django.apps
import django.conf
import django.contrib.auth.models
import django.core.management
import django.db.models
import django.db.transaction

import ezidapp.models.async_queue
import ezidapp.models.identifier

_L = logging.getLogger(__name__)

class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()

    def handle(self, *_, **opt):
        queue_classes = [
            ("binder", ezidapp.models.async_queue.BinderQueue),
            ("datacite", ezidapp.models.async_queue.DataciteQueue),
            ("crossref", ezidapp.models.async_queue.CrossrefQueue),
            ("searchindexer", ezidapp.models.async_queue.SearchIndexerQueue),
        ]
        queue_stats = {
            'download': {}
        }
        #Download queue is a different beast
        _L.info("Processing queue: download...")
        res = ezidapp.models.async_queue.DownloadQueue.objects\
                .all()\
                .values('stage')\
                .annotate(total=django.db.models.Count('stage'))\
                .order_by()
        for row in res:
            queue_stats['download'][row['stage']] = row['total']

        for q_class in queue_classes:
            q_name = q_class[0]
            _L.info(f"Processing queue: {q_name}")
            res = q_class[1].objects\
                .all()\
                .values('status')\
                .annotate(total=django.db.models.Count('status'))\
                .order_by()
            queue_stats[q_name] = {}
            for row in res:
                queue_stats[q_name][row['status']] = row['total']
        print(json.dumps(queue_stats, indent=2))
