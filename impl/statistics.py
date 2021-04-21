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


def getCrossRefQueueStatistics():
    """Returns a 4-tuple containing the numbers of identifiers in the Crossref
    queue by status: (awaiting submission, submitted, registered with warning,
    registration failed)."""
    q = ezidapp.models.crossref_queue.CrossrefQueue.objects.values("status").annotate(
        django.db.models.Count("status")
    )
    d = {}
    for r in q:
        d[r["status"]] = r["status__count"]
    return d.get("U", 0), d.get("S", 0), d.get("W", 0), d.get("F", 0)
