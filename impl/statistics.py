import types

import django.db.models
import ezidapp.models.crossref_queue
import ezidapp.models.download_queue
import ezidapp.models.datacite_queue
import ezidapp.models.binder_queue
import ezidapp.models.update_queue


def getUpdateQueueLength():
    return ezidapp.models.update_queue.UpdateQueue.objects.count()


def getBinderQueueLength():
    """Returns the length of the binder queue."""
    return ezidapp.models.binder_queue.BinderQueue.objects.count()


def getDataCiteQueueLength():
    """Returns the length of the DataCite queue."""
    return ezidapp.models.datacite_queue.DataciteQueue.objects.count()


def getDownloadQueueLength():
    """Returns the length of the batch download queue."""
    return ezidapp.models.download_queue.DownloadQueue.objects.count()


def getCrossrefQueueStatistics():
    """Returns a 4-tuple containing the numbers of identifiers in the Crossref
    queue by status: (awaiting submission, submitted, registered with warning,
    registration failed)."""
    q = ezidapp.models.crossref_queue.CrossrefQueue.objects.values("status").annotate(
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
