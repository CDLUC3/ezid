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
from datetime import datetime, timedelta
import time
import django.conf
import django.core.management
import django.db
import django.db.transaction

from .proc_base import AsyncProcessingIgnored, AsyncProcessingRemoteError, AsyncProcessingError

log = logging.getLogger(__name__)


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    name = __name__
    setting = 'DAEMONS_SEARCH_INDEXER_ENABLED'
    queue = ezidapp.models.async_queue.SearchIndexerQueue

    # note, the method is an overridden version to allow for occasional retries of supposedly "permanent" errors
    # such as network errors or a service being temporarily down or unresponsive.

    # It is kind of kludgy since it uses an infrequently running check every 5 minutes (300 seconds)
    # based on (current_time_in_seconds - submit_time_in_seconds) % 300 == 0 for up to 1 day since initial queuing.

    # It's possible it may not hit this exact remainder exactly every 5 minutes since
    # something may be running and not wake up at exactly 5 minute marks, but it will retry sometime soon since the
    # as though the default wake-up frequency for checking is every second

    # it may recheck up to 288 times (1 day / 5 minutes) before giving up on a task and leaving it as
    # a permanent error.

    # For the future we may want to consider a more sophisticated retry mechanism that maintains some
    # retry logic and state in the database for these queue models as well as more sophisticated notifications
    # on failures or a reporting system

    # this retry could break if the sleep time is changed to be longer than 1 second and might not trigger ever if the
    # wake up doesn't happen during the second it would trigger
    def run(self):
        """Run async processing loop forever.

        The async processes that don't use a queue based on AsyncQueueBase must override
        this to supply their own loop.

        This method is not called for disabled async processes.
        """
        assert self.queue is not None, "Must specify queue or override run()"

        while not self.terminated():
            self._possibly_reset_errors_for_retry()
            qs = self.queue.objects.filter(status=self.queue.UNSUBMITTED, ).order_by(
                "-seq"
            )[: django.conf.settings.DAEMONS_MAX_BATCH_SIZE]
            if not qs:
                self.sleep(django.conf.settings.DAEMONS_IDLE_SLEEP)
                continue

            for task_model in qs:
                self._possibly_reset_errors_for_retry()  # for up to 1 day after initial queuing

                try:
                    self.do_task(task_model)
                    task_model.status = self.queue.SUCCESS
                except AsyncProcessingIgnored:
                    task_model.status = self.queue.IGNORED
                except Exception as e:
                    if isinstance(e, AsyncProcessingRemoteError):
                        # This is a bit messy. Do not log a trace when the
                        # error is due to the remote service rejecting the request.
                        # Such an error is still permanent for the task though.
                        self.log.error(e)
                    else:
                        self.log.error('#' * 100)
                        self.log.exception(f'Exception when handling task "{task_model}"')

                    task_model.error = str(e)
                    # if self.is_permanent_error(e):
                    task_model.status = self.queue.FAILURE
                    task_model.errorIsPermanent = True
                    # raise  -- TODO: may want to notify or other things here if we need to know about these errors
                else:
                    task_model.submitTime = self.now_int()

                task_model.save()

            self.sleep(django.conf.settings.DAEMONS_BATCH_SLEEP)
        self.log.info("Exiting run loop.")

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

    def _possibly_reset_errors_for_retry(self):
        current_time = datetime.now()
        minutes = current_time.minute
        seconds = current_time.second

        # only run this on the 5 minute marks (up to 12 times an hour)
        if not (minutes % 5 == 0 and seconds == 0):
            return

        one_day_ago = datetime.now() - timedelta(days=1)

        # failures in the last day since enqueue time
        qs = self.queue.objects.filter(status=self.queue.FAILURE,
                                       enqueueTime__range=(one_day_ago.timestamp(), time.time())
                                      ).order_by("-seq")[: django.conf.settings.DAEMONS_MAX_BATCH_SIZE]

        for task_model in qs:
            try:
                task_model.status = self.queue.UNSUBMITTED

                # it becomes very confusing if we don't clear the error message and it succeeds following this,
                # the last error in 24 hours of retries will be the one that is shown afterward
                task_model.error = None
                task_model.errorIsPermanent = False
                task_model.save()

                self.log.info(f'Resetting task seq: "{task_model.seq}" to be retried')

            except Exception as e:
                log.error(f'Error resetting task "{task_model}" for retry: {e}')
                # raise e
