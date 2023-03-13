#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Asynchronous DataCite processing

This background process takes tasks from the DataciteQueue
and performs the specified actions to set infomration in
Datacite to correspond with the identifier and its
metadata in EZID.
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
    name = __name__
    setting = 'DAEMONS_DATACITE_ENABLED'
    queue = ezidapp.models.async_queue.DataciteQueue

    def create(self, task_model: ezidapp.models.async_queue.DataciteQueue):
        if self._is_eligible(task_model):
            self._create_or_update(task_model)

    def update(self, task_model: ezidapp.models.async_queue.DataciteQueue):
        if self._is_eligible(task_model):
            self._create_or_update(task_model)

    def delete(self, task_model: ezidapp.models.async_queue.DataciteQueue):
        # We cannot delete a DOI on DataCite, so we disable it by setting an invalid
        # target URL and removing it from DataCite's search index. See
        # deactivateIdentifier() for additional info.
        if not task_model.refIdentifier.isDatacite:
            return
        # TODO: need to handle error conditions
        if self._is_eligible(task_model):
            ref_id = task_model.refIdentifier
            doi = ref_id.identifier[4:]
            datacenter = str(ref_id.datacenter)
            impl.datacite.setTargetUrl(doi, "http://datacite.org/invalidDOI", datacenter)
            impl.datacite.deactivateIdentifier(doi, datacenter)

    def _is_eligible(self, task_model: ezidapp.models.async_queue.DataciteQueue):
        """Return True if task is eligible for this process"""
        is_eligible = task_model.refIdentifier.isDatacite and not task_model.refIdentifier.isTest
        if not is_eligible:
            log.debug(f'Skipping ineligible task: {task_model}')
        return is_eligible

    def _create_or_update(self, task_model: ezidapp.models.async_queue.DataciteQueue):
        ref_id: ezidapp.models.identifier.RefIdentifier = task_model.refIdentifier
        # doi:10.1234/foo
        #     ^---------
        doi: str = ref_id.identifier[4:]
        metadata = ref_id.metadata
        metadata['_profile'] = str(ref_id.profile)
        datacenter = str(ref_id.datacenter)
        r = impl.datacite.uploadMetadata(doi, {}, metadata, True, datacenter)
        # r can be:
        # None == success
        # string == error message, something wrong with payload
        # exception == something else went wrong.
        # Exceptions are handled in the outer run method, so don't handle here.
        #
        if r is not None:
            log.error("datacite.uploadMetadata returned: %s", r)
            if isinstance(r, str):
                raise ezidapp.management.commands.proc_base.AsyncProcessingRemoteError(r)
            raise ezidapp.management.commands.proc_base.AsyncProcessingError(r)

        # This should set the datacite target url to identifier.resolverTarget
        # to take into consideration reserved or unavailable status.
        r = impl.datacite.setTargetUrl(doi, ref_id.resolverTarget, datacenter)

        # r can be:
        #   None on success
        #   a string error message if the target URL was not accepted by DataCite
        #   a thrown exception on other error.
        if r is not None:
            log.error("datacite.setTargetUrl returned: %s", r)
            if isinstance(r, str):
                raise ezidapp.management.commands.proc_base.AsyncProcessingRemoteError(r)
            raise ezidapp.management.commands.proc_base.AsyncProcessingError(r)
        # check for non-public and adjust to suit
        if metadata.get("_is", "public") != "public" or metadata.get("_x", "yes") != "yes":
            r = impl.datacite.deactivateIdentifier(doi, datacenter)
            if r is not None:
                log.error("datacite.deactivateIdentifier returned: %s", r)
                if isinstance(r, str):
                    raise ezidapp.management.commands.proc_base.AsyncProcessingRemoteError(r)
                raise ezidapp.management.commands.proc_base.AsyncProcessingError(r)
