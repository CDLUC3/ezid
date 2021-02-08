# =============================================================================
#
# EZID :: binder_async.py
#
# Asynchronous N2T binder processing.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2017, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import uuid

import django.conf

import ezidapp.models.binder_queue
import impl.config
import impl.noid_egg
import impl.register_async

_daemonEnabled = [None]
_threadName = [None]


def _create(sh, rows, id_str, metadata):
    impl.register_async.callWrapper(
        sh, rows, "noid_egg.setElements", impl.noid_egg.setElements, id_str, metadata
    )


def _update(sh, rows, id_str, metadata):
    m = impl.register_async.callWrapper(
        sh, rows, "noid_egg.getElements", impl.noid_egg.getElements, id_str
    )
    if m is None:
        m = {}
    for k, v in list(metadata.items()):
        if m.get(k) == v:
            del m[k]
        else:
            m[k] = v
    for k in list(m.keys()):
        if k not in metadata:
            m[k] = ""
    if len(m) > 0:
        impl.register_async.callWrapper(
            sh, rows, "noid_egg.setElements", impl.noid_egg.setElements, id_str, m
        )


def _delete(sh, rows, id_str, _metadata):
    impl.register_async.callWrapper(
        sh, rows, "noid_egg.deleteIdentifier", impl.noid_egg.deleteIdentifier, id_str
    )


def _batchCreate(sh, rows, batch):
    impl.register_async.callWrapper(
        sh, rows, "noid_egg.batchSetElements", impl.noid_egg.batchSetElements, batch
    )


def _batchDelete(sh, rows, batch):
    impl.register_async.callWrapper(
        sh,
        rows,
        "noid_egg.batchDeleteIdentifier",
        impl.noid_egg.batchDeleteIdentifier,
        [identifier for identifier, metadata in batch],
    )


def enqueueIdentifier(identifier, operation, blob):
    """Adds an identifier to the binder asynchronous processing queue.

    'identifier' should be the normalized, qualified identifier, e.g.,
    "doi:10.5060/FOO".  'operation' is the identifier operation and
    should be one of the strings "create", "update", or "delete". 'blob'
    is the identifier's metadata dictionary in blob form.
    """
    impl.register_async.enqueueIdentifier(
        ezidapp.models.binder_queue.BinderQueue, identifier, operation, blob
    )


def getQueueLength():
    """Returns the length of the binder queue."""
    return ezidapp.models.binder_queue.BinderQueue.objects.count()


def loadConfig():
    _daemonEnabled[0] = (
        django.conf.settings.DAEMON_THREADS_ENABLED
        and impl.config.get("daemons.binder_enabled").lower() == "true"
    )
    if _daemonEnabled[0]:
        # noinspection PyTypeChecker
        _threadName[0] = uuid.uuid1().hex
        impl.register_async.launch(
            "binder",
            ezidapp.models.binder_queue.BinderQueue,
            _create,
            _update,
            _delete,
            _batchCreate,
            None,
            _batchDelete,
            int(impl.config.get("daemons.binder_num_worker_threads")),
            int(impl.config.get("daemons.binder_processing_idle_sleep")),
            int(impl.config.get("daemons.binder_processing_error_sleep")),
            _daemonEnabled,
            _threadName,
        )
