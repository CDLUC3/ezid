# =============================================================================
#
# EZID :: SearchDbDaemon.py
#
# Background identifier processing.
#
# This module should be imported at server startup so that its daemon
# thread is started.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2014, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import impl.daemon.daemon_base
import django.conf
import logging
import threading
import time

import django.conf
import django.db
import django.db.transaction

import ezidapp.models.search_identifier
import ezidapp.models.update_queue
import impl.daemon.binder
import impl.daemon.crossref
import impl.daemon.datacite
import impl.log
import impl.search_util
import impl.util


logger = logging.getLogger(__name__)


class SearchDbDaemon(impl.daemon.daemon_base.DaemonBase):
    def __init__(self):
        super(SearchDbDaemon, self).__init__()

        self._runningThreads = set()

        # _threadName = None
        # int(django.conf.settings.DAEMONS_CROSSREF_PROCESSING_IDLE_SLEEP) = None
        # django.conf.settings.CROSSREF_ENABLED = (
        #     django.conf.settings.DAEMON_THREADS_ENABLED
        #     and django.conf.settings.DAEMONS_SEARCHDB_ENABLED
        # )
        #
        # if django.conf.settings.CROSSREF_ENABLED:
        #     int(django.conf.settings.DAEMONS_CROSSREF_PROCESSING_IDLE_SLEEP) = int(django.conf.settings.DAEMONS_BACKGROUND_PROCESSING_IDLE_SLEEP)
        #     _threadName = uuid.uuid1().hex
        #
        #     t = threading.Thread(target=_searchDbDaemon, name=_threadName)
        #     t.setDaemon(True)
        #     t.start()

    #

    def _updateSearchDatabase(self, identifier, operation, metadata, _blob):
        if operation in ["create", "update"]:
            ezidapp.models.search_identifier.updateFromLegacy(identifier, metadata)
        elif operation == "delete":
            ezidapp.models.search_identifier.SearchIdentifier.objects.filter(
                identifier=identifier
            ).delete()
        else:
            assert False, "unrecognized operation"

    def _checkContinue(self):
        return (
            django.conf.settings.CROSSREF_ENABLED
            and threading.currentThread().getName() == self._threadName
        )

    def _searchDbDaemon(self):
        self._lock.acquire()

        try:
            logger.debug(
                'Running background processing threads: count={}'.format(
                    len(self._runningThreads)
                )
            )
            logger.debug('New thread: {}'.format(threading.currentThread().getName()))
            self._runningThreads.add(threading.currentThread().getName())
            logger.debug('New count: {}'.format(threading.active_count()))

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
                totalWaitTime += int(
                    django.conf.settings.DAEMONS_CROSSREF_PROCESSING_IDLE_SLEEP
                )
                # noinspection PyTypeChecker
                time.sleep(
                    int(django.conf.settings.DAEMONS_CROSSREF_PROCESSING_IDLE_SLEEP)
                )
        except AssertionError as e:
            impl.log.otherError("_searchDbDaemon", e)
        # Regular processing.
        while self._checkContinue():
            try:
                update_list = list(
                    ezidapp.models.update_queue.UpdateQueue.objects.all().order_by(
                        "seq"
                    )[:1000]
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
                                break

                        with django.db.transaction.atomic():
                            if not update_model.actualObject.isReserved:
                                impl.daemon.binder.enqueueIdentifier(
                                    update_model.identifier,
                                    update_model.get_operation_display(),
                                    blob,
                                )
                                if update_model.updateExternalServices:
                                    if update_model.actualObject.isDatacite:
                                        if not update_model.actualObject.isTest:
                                            impl.daemon.datacite.enqueueIdentifier(
                                                update_model.identifier,
                                                update_model.get_operation_display(),
                                                blob,
                                            )
                                    elif update_model.actualObject.isCrossref:
                                        impl.daemon.crossref.enqueueIdentifier(
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
                    time.sleep(
                        int(django.conf.settings.DAEMONS_CROSSREF_PROCESSING_IDLE_SLEEP)
                    )
            except Exception as e:
                logging.exception(f'Exception in searchDbDaemon thread: {str(e)}')
                impl.log.otherError("searchDb._searchDbDaemon", e)
                django.db.connections["default"].close()
                django.db.connections["search"].close()
                # noinspection PyTypeChecker
                time.sleep(
                    int(django.conf.settings.DAEMONS_CROSSREF_PROCESSING_IDLE_SLEEP)
                )
        self._lock.acquire()
        try:
            self._runningThreads.remove(threading.currentThread().getName())
        finally:
            self._lock.release()
