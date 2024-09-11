#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import types

import django.db.models
import ezidapp.models.async_queue


def getDataCiteQueueLength():
    """Return the length of the DataCite queue."""
    return ezidapp.models.async_queue.DataciteQueue.objects.count()


def getDownloadQueueLength():
    """Return the length of the batch download queue."""
    return ezidapp.models.async_queue.DownloadQueue.objects.count()


def getCrossrefQueueStatistics():
    """Return a 4-tuple containing the numbers of identifiers in the Crossref
    queue by status: (awaiting submission, submitted, registered with warning,
    registration failed)."""
    q = ezidapp.models.async_queue.CrossrefQueue.objects.values("status").annotate(
        django.db.models.Count("status")
    )
    status_code_to_text = {
        'U': 'awaiting_submission',
        'S': 'submitted',
        'W': 'registered_with_warning',
        'F': 'registration_failed',
    }
    default_dict = {text: 0 for text in status_code_to_text.values()}
    return types.SimpleNamespace(
        **{
            **default_dict,
            **{
                status_code_to_text[row['status']]: row['status__count'] for row in q
            },
        }
    )
