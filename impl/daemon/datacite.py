# =============================================================================
#
# EZID :: datacite.py
#
# Asynchronous DataCite processing.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import impl.daemon.daemon_base
import uuid

import django.conf

import ezidapp.models.datacite_queue
import impl.datacite
import impl.daemon.register_async


class DataCiteDaemon(impl.daemon.daemon_base.DaemonBase):
    def __init__(self):
        super(DataCiteDaemon, self).__init__()

    def _uploadMetadata(self, doi, metadata, datacenter):
        r = impl.datacite.uploadMetadata(doi[4:], {}, metadata, True, datacenter)
        assert type(r) is not str, "unexpected return: " + r

    def _setTargetUrl(self, doi, targetUrl, datacenter):
        r = impl.datacite.setTargetUrl(doi[4:], targetUrl, datacenter)
        assert type(r) is not str, "unexpected return: " + r

    def _overwrite(self, sh, rows, doi, metadata):
        impl.daemon.register_async.callWrapper(
            sh,
            rows,
            "datacite.uploadMetadata",
            self._uploadMetadata,
            doi,
            metadata,
            metadata["_d"],
        )
        impl.daemon.register_async.callWrapper(
            sh,
            rows,
            "datacite.setTargetUrl",
            self._setTargetUrl,
            doi,
            metadata["_t"],
            metadata["_d"],
        )
        if (
            metadata.get("_is", "public") != "public"
            or metadata.get("_x", "yes") != "yes"
        ):
            impl.daemon.register_async.callWrapper(
                sh,
                rows,
                "datacite.deactivate",
                impl.datacite.deactivate,
                doi[4:],
                metadata["_d"],
            )

    def _delete(self, sh, rows, doi, metadata):
        # We can't actually delete a DOI, so we do the next best thing...
        impl.daemon.register_async.callWrapper(
            sh,
            rows,
            "datacite.setTargetUrl",
            self._setTargetUrl,
            doi,
            "http://datacite.org/invalidDOI",
            metadata["_d"],
        )
        impl.daemon.register_async.callWrapper(
            sh,
            rows,
            "datacite.deactivate",
            impl.datacite.deactivate,
            doi[4:],
            metadata["_d"],
        )

    def enqueueIdentifier(self, identifier, operation, blob):
        """Adds an identifier to the DataCite asynchronous processing queue.

        'identifier' should be the normalized, qualified identifier, e.g.,
        "doi:10.5060/FOO".  'operation' is the identifier operation and
        should be one of the strings "create", "update", or "delete". 'blob'
        is the identifier's metadata dictionary in blob form.
        """
        impl.daemon.register_async.enqueueIdentifier(
            ezidapp.models.datacite_queue.DataciteQueue, identifier, operation, blob
        )

    def getQueueLength(self):
        """Returns the length of the DataCite queue."""
        return ezidapp.models.datacite_queue.DataciteQueue.objects.count()

    _daemonEnabled = [None]
    _threadName = [None]

    _daemonEnabled[0] = (
        django.conf.settings.DAEMON_THREADS_ENABLED
        and django.conf.settings.DAEMONS_DATACITE_ENABLED
    )

    if _daemonEnabled[0]:
        # noinspection PyTypeChecker
        _threadName[0] = uuid.uuid1().hex
        impl.daemon.register_async.launch(
            "datacite",
            ezidapp.models.datacite_queue.DataciteQueue,
            _overwrite,
            _overwrite,
            _delete,
            None,
            None,
            None,
            int(django.conf.settings.DAEMONS_DATACITE_NUM_WORKER_THREADS),
            int(django.conf.settings.DAEMONS_DATACITE_PROCESSING_IDLE_SLEEP),
            int(django.conf.settings.DAEMONS_DATACITE_PROCESSING_ERROR_SLEEP),
            _daemonEnabled,
            _threadName,
        )

    # django.conf.settings.EZID_BASE_URL = django.conf.settings.EZID_BASE_URL
    # _gzipCommand = django.conf.settings.GZIP_COMMAND
    # int(django.conf.settings.DAEMONS_CROSSREF_PROCESSING_IDLE_SLEEP) = int(django.conf.settings.DAEMONS_DOWNLOAD_PROCESSING_IDLE_SLEEP)
    # _threadName = None
    # _usedFilenames = None
    # _zipCommand = django.conf.settings.ZIP_COMMAND
