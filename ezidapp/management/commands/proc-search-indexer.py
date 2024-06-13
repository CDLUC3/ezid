#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Index identifiers for search

This async process keeps the SearchIdentifier model in sync with the StoreIdentifier
model.

The StoreIdentifier and SearchIdentifier models hold the same information, but the
SearchIdentifier model adds a set of indexes that make inserts expensive. So we add and
update StoreIdentifier "inline", while processing a request, and update SearchIdentifier
asynchronously.

As the changes made to the StoreIdentifier are wrapped in a transaction that covers the
request, partial changes in StoreIdentifier are not visible to this process, and all
changes to a single identifier are handled as a single unit after the request is
completed.
"""

import logging

import ezidapp.management.commands.proc_base
import ezidapp.models.async_queue
import ezidapp.models.identifier
from impl.open_search_doc import OpenSearchDoc
from django.db import transaction
from django.db import DatabaseError

log = logging.getLogger(__name__)


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    name = __name__
    setting = 'DAEMONS_SEARCH_INDEXER_ENABLED'
    queue = ezidapp.models.async_queue.SearchIndexerQueue

    def create(self, task_model):
        if not self._is_anonymous(task_model):
            self._update_or_create(task_model.refIdentifier)
        else:
            log.debug(f'Skipped create: Anonymous owner')

    def update(self, task_model):
        if not self._is_anonymous(task_model):
            self._update_or_create(task_model.refIdentifier)
        else:
            log.debug('Skipped create: Anonymous owner')

    def delete(self, task_model):
        if not self._is_anonymous(task_model):
            # search model
            target_ids = ezidapp.models.identifier.SearchIdentifier.objects.filter(
                identifier=task_model.refIdentifier.identifier,
            )

            try:
                with transaction.atomic():
                    for target_id in target_ids:
                        open_s = OpenSearchDoc(identifier=task_model.refIdentifier)
                        if not open_s.remove_from_index():
                            raise DatabaseError('Error deleting from OpenSearch index')  # skip DB delete
                    target_ids.delete()
            except DatabaseError as e:
                log.error(f'Error deleting, rolling transaction back: {e}')
                if 'OpenSearch' not in str(e):
                    # reindex the identifiers in OpenSearch that failed to delete from the database
                    for target_id in target_ids:
                        OpenSearchDoc.index_from_search_identifier(search_identifier=target_id)
                raise e


    def _is_anonymous(self, task_model):
        return task_model.refIdentifier.owner is None

    def _update_or_create(
        self,
        ref_id_model: ezidapp.models.identifier.RefIdentifier,
    ):
        log.debug(f'ref_id_model="{ref_id_model}"')
        search_id_model = self._ref_id_to_search_id(ref_id_model)
        search_id_model.computeComputedValues()
        try:
            with transaction.atomic():
                search_id_model.save()  # if error saving skips to exception
                open_s = OpenSearchDoc(identifier=ref_id_model)
                is_good = open_s.index_document()
                if not is_good:
                    raise DatabaseError('Error indexing in OpenSearch')  # should trigger rollback
        except DatabaseError as e:
            log.error(f'Error saving, rolling transaction back: {e}')
            if 'OpenSearch' not in str(e):
                # it didn't save to db, see if searchIdentifier exists in the database (from previous save)
                existing_count = ezidapp.models.identifier.SearchIdentifier.objects.filter(
                    identifier=search_id_model.identifier,
                ).count()
                if existing_count == 0:
                    # it's not in the SearchIdentifier db table, so remove it from OpenSearch
                    open_s = OpenSearchDoc(identifier=ref_id_model)
                    open_s.remove_from_index()
            raise e

    def _ref_id_to_search_id(self, ref_id_model):
        try:
            search_id_model = ezidapp.models.identifier.SearchIdentifier.objects.get(
                identifier=ref_id_model.identifier
            )
        except ezidapp.models.identifier.SearchIdentifier.DoesNotExist:
            search_id_model = ezidapp.models.identifier.SearchIdentifier(
                identifier=ref_id_model.identifier
            )
        for field_obj in ref_id_model._meta.fields:
            field_name = field_obj.attname
            if field_name not in ('id', 'identifier'):
                v = getattr(ref_id_model, field_name)
                setattr(search_id_model, field_name, v)
        return search_id_model
