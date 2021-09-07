"""Background identifier processing
"""

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import logging
import threading
import time

import django.conf
import django.db
import django.db.transaction

import ezidapp.management.commands.proc_base
import ezidapp.models.identifier
import impl.enqueue
import impl.log
import impl.nog.util
import impl.search_util
import impl.util

log = logging.getLogger(__name__)


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    display = 'SearchDB'
    name = 'searchdb'
    setting = 'DAEMONS_SEARCHDB_ENABLED'

    def __init__(self):
        super(Command, self).__init__(__name__)

    def add_arguments(self, parser):
        super().add_arguments(parser)

    def handle_daemon(self, *_, **opt):
        pass

    def _updateSearchDatabase(self, identifier, operation, metadata, _blob):
        if operation in ["create", "update"]:
            ezidapp.models.identifier.updateFromLegacy(identifier, metadata)
        elif operation == "delete":
            ezidapp.models.identifier.SearchIdentifier.objects.filter(
                identifier=identifier
            ).delete()
        else:
            assert False, "unrecognized operation"

    def _checkContinue(self):
        return (
            django.conf.settings.CROSSREF_ENABLED
            and threading.currentThread().getName() == self._threadName
        )

    def run(self):
        self._lock.acquire()

        try:
            log.debug(
                'Running background processing threads: count={}'.format(len(self._runningThreads))
            )
            log.debug('New thread: {}'.format(threading.currentThread().getName()))
            self._runningThreads.add(threading.currentThread().getName())
            log.debug('New count: {}'.format(threading.active_count()))

        finally:
            self._lock.release()

        # If we were started due to a reload, we wait for the previous
        # thread to terminate... but not forever.  60 seconds is arbitrary.
        totalWaitTime = 0
        try:
            while self._checkContinue():
                self._lock.acquire()
                try:
                    n = len(self._runningThreads)
                finally:
                    self._lock.release()
                if n == 1:
                    break
                assert (
                    totalWaitTime <= 60
                ), "new searchDbDaemon daemon started before previous daemon terminated"
                totalWaitTime += int(django.conf.settings.DAEMONS_CROSSREF_PROCESSING_IDLE_SLEEP)
                # noinspection PyTypeChecker
                time.sleep(int(django.conf.settings.DAEMONS_CROSSREF_PROCESSING_IDLE_SLEEP))
        except AssertionError as e:
            log.exception(' AssertionError as e')
            self.otherError("_searchDbDaemon", e)

        # Regular processing.
        while self._checkContinue():
            try:
                update_list = list(
                    ezidapp.models.async_queue.AsyncQueue.objects.all().order_by("seq")[:1000]
                )
                if len(update_list) > 0:
                    for update_model in update_list:
                        if not self._checkContinue():
                            break
                        # The use of legacy representations and blobs will go away soon.
                        metadata = update_model.actualObject.toLegacy()
                        blob = impl.util.blobify(metadata)
                        if update_model.actualObject.owner is not None:
                            try:
                                impl.search_util.withAutoReconnect(
                                    "searchDb._updateSearchDatabase",
                                    lambda: self._updateSearchDatabase(
                                        update_model.identifier,
                                        update_model.get_operation_display(),
                                        metadata,
                                        blob,
                                    ),
                                    self._checkContinue,
                                )
                            except impl.search_util.AbortException:
                                log.exception(' impl.search_util.AbortException')
                                break

                        with django.db.transaction.atomic():
                            if not update_model.actualObject.isReserved:
                                impl.enqueue.enqueueBinderIdentifier(
                                    update_model.identifier,
                                    update_model.get_operation_display(),
                                    blob,
                                )
                                if update_model.updateExternalServices:
                                    if update_model.actualObject.isDatacite:
                                        if not update_model.actualObject.isTest:
                                            impl.enqueue.enqueueDataCiteIdentifier(
                                                update_model.identifier,
                                                update_model.get_operation_display(),
                                                blob,
                                            )
                                    elif update_model.actualObject.isCrossref:
                                        impl.enqueue.enqueueCrossrefIdentifier(
                                            update_model.identifier,
                                            update_model.get_operation_display(),
                                            metadata,
                                            blob,
                                        )
                            update_model.delete()
                else:
                    django.db.connections["default"].close()
                    django.db.connections["search"].close()
                    # noinspection PyTypeChecker
                    time.sleep(int(django.conf.settings.DAEMONS_CROSSREF_PROCESSING_IDLE_SLEEP))
            except Exception as e:
                log.exception(' Exception as e')
                logging.exception(f'Exception in searchDbDaemon thread: {str(e)}')
                self.otherError("searchDb._searchDbDaemon", e)
                django.db.connections["default"].close()
                django.db.connections["search"].close()
                # noinspection PyTypeChecker
                time.sleep(int(django.conf.settings.DAEMONS_CROSSREF_PROCESSING_IDLE_SLEEP))
        self._lock.acquire()
        try:
            self._runningThreads.remove(threading.currentThread().getName())
        finally:
            self._lock.release()
