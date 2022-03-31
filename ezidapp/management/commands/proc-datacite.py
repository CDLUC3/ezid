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
        if task_model.refIdentifier.isDatacite:
            self._create_or_update(task_model)
        else:
            log.debug('Create skipped: isDatacite == False')

    def update(self, task_model):
        if task_model.refIdentifier.isDatacite:
            self._create_or_update(task_model)
        else:
            log.debug('Update skipped: isDatacite == False')

    def delete(self, task_model):
        # We can't actually delete a DOI, so we do the next best thing...
        # TODO: need to handle error conditions
        ref_id = task_model.refIdentifier
        doi = ref_id.identifier[4:]
        datacenter = ref_id.datacenter
        impl.datacite.setTargetUrl(doi, "http://datacite.org/invalidDOI", datacenter)
        impl.datacite.deactivateIdentifier(doi, datacenter)

    def _create_or_update(self, task_model):
        ref_id = task_model.refIdentifier
        doi = ref_id.identifier[4:]
        metadata = ref_id.metadata
        datacenter = ref_id.datacenter
        r = impl.datacite.uploadMetadata(doi, {}, metadata, True, datacenter)
        # r can be:
        # None == success
        # string == error message, something wrong with payload
        # exception == something else went wrong.
        # Exceptions are handled in the outer run method, so don't handle here.
        #
        # TODO: DRY this a bit
        if r is not None:
            log.error("datacite.uploadMetadata returned: %s", r)
            if isinstance(r, str):
                raise ezidapp.management.commands.proc_base.AsyncProcessingRemoteError(r)
            raise ezidapp.management.commands.proc_base.AsyncProcessingError(r)
        r = impl.datacite.setTargetUrl(doi, ref_id.target, datacenter)
        # r can be:
        #   None on success
        #   a string error message if the target URL was not accepted by DataCite
        #   a thrown exception on other error.
        if r is not None:
            log.error("datacite.setTargetUrl returned: %s", r)
            if isinstance(r, str):
                raise ezidapp.management.commands.proc_base.AsyncProcessingRemoteError(r)
            raise ezidapp.management.commands.proc_base.AsyncProcessingError(r)
        if metadata.get("_is", "public") != "public" or metadata.get("_x", "yes") != "yes":
            r = impl.datacite.deactivateIdentifier(doi, datacenter)
            if r is not None:
                log.error("datacite.deactivateIdentifier returned: %s", r)
                if isinstance(r, str):
                    raise ezidapp.management.commands.proc_base.AsyncProcessingRemoteError(r)
                raise ezidapp.management.commands.proc_base.AsyncProcessingError(r)
