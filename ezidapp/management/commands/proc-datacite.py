#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Asynchronous DataCite processing
"""

import logging

import django.conf
import django.core.management

import ezidapp.management.commands.proc_base
import ezidapp.models.async_queue
import impl.datacite
import impl.nog.util
import ezidapp.models.identifier

log = logging.getLogger(__name__)


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    display = 'DataCite'
    setting = 'DAEMONS_DATACITE_ENABLED'
    queue = ezidapp.models.async_queue.DataciteQueue

    def create(self, task_model):
        pass

    def update(self, task_model):
        pass

    def delete(self, task_model):
        pass

    def _uploadMetadata(self, doi, metadata, datacenter):
        r = impl.datacite.uploadMetadata(doi[4:], {}, metadata, True, datacenter)
        assert type(r) is not str, "unexpected return: " + r

    def _setTargetUrl(self, doi, targetUrl, datacenter):
        r = impl.datacite.setTargetUrl(doi[4:], targetUrl, datacenter)
        assert type(r) is not str, "unexpected return: " + r

    def _overwrite(self, rows, doi, metadata):
        self._uploadMetadata(rows, doi, metadata, metadata["_d"])
        self._setTargetUrl(rows,doi, metadata["_t"], metadata["_d"])
        if (
            metadata.get("_is", "public") != "public"
            or metadata.get("_x", "yes") != "yes"
        ):
            impl.datacite.deactivate(rows, doi[4:], metadata["_d"])

    def _delete(self, rows, doi, metadata):
        # We can't actually delete a DOI, so we do the next best thing...
        self._setTargetUrl(rows, doi, "http://datacite.org/invalidDOI",
                         metadata["_d"])
        impl.datacite.deactivate(rows, doi[4:], metadata["_d"])
