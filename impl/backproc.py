# =============================================================================
#
# EZID :: backproc.py
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

import logging
import threading
import time
import uuid

import django.conf
import django.db
import django.db.transaction

from . import binder_async
from . import config
from . import crossref
from . import datacite_async
import ezidapp.models
import ezidapp.models.search_identifier
from . import log
from . import search_util
from . import util

_enabled = None
_lock = threading.Lock()
_runningThreads = set()
_threadName = None
_idleSleep = None


logger = logging.getLogger(__name__)


def _updateSearchDatabase(identifier, operation, metadata, blob):
    if operation in ["create", "update"]:
        ezidapp.models.search_identifier.updateFromLegacy(identifier, metadata)
    elif operation == "delete":
        ezidapp.models.SearchIdentifier.objects.filter(identifier=identifier).delete()
    else:
        assert False, "unrecognized operation"


def _checkContinue():
    return _enabled and threading.currentThread().getName() == _threadName


def _backprocDaemon():
    _lock.acquire()

    try:
        logger.debug('Running background processing threads: count={}'.format(len(_runningThreads)))
        logger.debug('New thread: {}'.format(threading.currentThread().getName()))
        _runningThreads.add(threading.currentThread().getName())
        logger.debug('New count: {}'.format(threading.active_count()))

    finally:
        _lock.release()
    # If we were started due to a reload, we wait for the previous
    # thread to terminate... but not forever.  60 seconds is arbitrary.
    totalWaitTime = 0
    try:
        while _checkContinue():
            _lock.acquire()
            try:
                n = len(_runningThreads)
            finally:
                _lock.release()
            if n == 1:
                break
            assert (
                totalWaitTime <= 60
            ), "new backproc daemon started before previous daemon terminated"
            totalWaitTime += _idleSleep
            time.sleep(_idleSleep)
    except AssertionError as e:
        log.otherError("backproc._backprocDaemon", e)
    # Regular processing.
    while _checkContinue():
        try:
            update_list = list(ezidapp.models.UpdateQueue.objects.all().order_by("seq")[:1000])
            if len(update_list) > 0:
                for update_model in update_list:
                    if not _checkContinue():
                        break
                    # The use of legacy representations and blobs will go away soon.
                    metadata = update_model.actualObject.toLegacy()
                    blob = util.blobify(metadata)
                    if update_model.actualObject.owner != None:
                        try:
                            search_util.withAutoReconnect(
                                "backproc._updateSearchDatabase",
                                lambda: _updateSearchDatabase(
                                    update_model.identifier,
                                    update_model.get_operation_display(),
                                    metadata,
                                    blob,
                                ),
                                _checkContinue,
                            )
                        except search_util.AbortException:
                            break
                    with django.db.transaction.atomic():
                        if not update_model.actualObject.isReserved:
                            binder_async.enqueueIdentifier(
                                update_model.identifier, update_model.get_operation_display(), blob
                            )
                            if update_model.updateExternalServices:
                                if update_model.actualObject.isDatacite:
                                    if not update_model.actualObject.isTest:
                                        datacite_async.enqueueIdentifier(
                                            update_model.identifier,
                                            update_model.get_operation_display(),
                                            blob,
                                        )
                                elif update_model.actualObject.isCrossref:
                                    crossref.enqueueIdentifier(
                                        update_model.identifier,
                                        update_model.get_operation_display(),
                                        metadata,
                                        blob,
                                    )
                        update_model.delete()
            else:
                django.db.connections["default"].close()
                django.db.connections["search"].close()
                time.sleep(_idleSleep)
        except Exception as e:
            log.otherError("backproc._backprocDaemon", e)
            django.db.connections["default"].close()
            django.db.connections["search"].close()
            time.sleep(_idleSleep)
    _lock.acquire()
    try:
        _runningThreads.remove(threading.currentThread().getName())
    finally:
        _lock.release()


def loadConfig():
    global _enabled, _idleSleep, _threadName
    _enabled = (
        django.conf.settings.DAEMON_THREADS_ENABLED
        and config.get("daemons.backproc_enabled").lower() == "true"
    )
    if _enabled:
        _idleSleep = int(config.get("daemons.background_processing_idle_sleep"))
        _threadName = uuid.uuid1().hex
        t = threading.Thread(target=_backprocDaemon, name=_threadName)
        t.setDaemon(True)
        t.start()
