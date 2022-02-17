#  Copyright©2022, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Realtime monitoring of EZID status
"""
import django.contrib.auth.mixins
import django.db.models
import django.http
import django.views

import ezidapp.models.async_queue
import ezidapp.models.news_feed
import impl.ezid
import impl.statistics

# Queues derived from AsyncQueueBase
QUEUE_MODEL_TUP = (
    ezidapp.models.async_queue.BinderQueue,
    ezidapp.models.async_queue.CrossrefQueue,
    ezidapp.models.async_queue.DataciteQueue,
    ezidapp.models.async_queue.SearchIndexerQueue,
)

# "Non-standard" queues
# ezidapp.models.async_queue.DownloadQueue,
# ezidapp.models.news_feed.NewsFeed,


class Queues(django.contrib.auth.mixins.LoginRequiredMixin, django.views.View):
    def get(self, request, *args, **kwargs):
        activeUsers, waitingUsers, isPaused = impl.ezid.getStatus()
        return django.http.JsonResponse(
            {
                'ActiveOperations': sum(activeUsers.values()),
                'WaitingRequests': sum(waitingUsers.values()),
                'IsPaused': isPaused,
                'DownloadQueue': {
                    'count': ezidapp.models.async_queue.DownloadQueue.objects.count()
                },
                'NewsFeed': {'count': ezidapp.models.news_feed.NewsFeed.objects.count()},
                **self.group_count('status'),
                **self.group_count('operation'),
            },
            json_dumps_params={'indent': 2},
        )

    def group_count(self, col_name):
        return {
            # queue_model.__name__: queue_model.objects.count()
            queue_model.__name__: list(
                queue_model.objects.values(col_name)
                .order_by(col_name)
                .annotate(count=django.db.models.Count(col_name))
                .all()
            )
            for queue_model in QUEUE_MODEL_TUP
        }
