#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Asynchronous DataCite processing
"""

import logging

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
        self._overwrite(task_model)

    def update(self, task_model):
        self._overwrite(task_model)

    def delete(self, task_model):
        # We can't actually delete a DOI, so we do the next best thing...
        ref_id = task_model.refIdentifier
        doi = ref_id.identifier[4:]
        datacenter = ref_id.datacenter
        impl.datacite.setTargetUrl(doi, "http://datacite.org/invalidDOI", datacenter)
        impl.datacite.deactivateIdentifier(doi, datacenter)

    def _overwrite(self, task_model):
        ref_id = task_model.refIdentifier
        doi = ref_id.identifier[4:]
        metadata = ref_id.metadata
        datacenter = ref_id.datacenter
        r = impl.datacite.uploadMetadata(doi, {}, metadata, True, datacenter)
        assert type(r) is not str, f"Unexpected return: {repr(r)}"
        r = impl.datacite.setTargetUrl(doi, ref_id.target, datacenter)
        assert type(r) is not str, f"Unexpected return: {repr(r)}"
        if metadata.get("_is", "public") != "public" or metadata.get("_x", "yes") != "yes":
            impl.datacite.deactivateIdentifier(doi, datacenter)
