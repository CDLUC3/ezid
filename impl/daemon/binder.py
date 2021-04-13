# =============================================================================
#
# EZID :: binder.py
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

import django.conf
import uuid

import django.conf

import ezidapp.models.binder_queue
import impl.noid_egg
import impl.daemon.register_async
# import impl.daemon.daemon_base


class BinderDaemon(impl.daemon.daemon_base.DaemonBase):
    # import impl.noid_egg

    def __init__(self):
        super(BinderDaemon, self).__init__()

    def _create(self, sh, rows, id_str, metadata):
        impl.daemon.register_async.callWrapper(
            sh,
            rows,
            "noid_egg.setElements",
            impl.noid_egg.setElements,
            id_str,
            metadata,
        )

    def _update(self, sh, rows, id_str, metadata):
        m = impl.daemon.register_async.callWrapper(
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
            impl.daemon.register_async.callWrapper(
                sh, rows, "noid_egg.setElements", impl.noid_egg.setElements, id_str, m
            )

    def _delete(self, sh, rows, id_str, _metadata):
        impl.daemon.register_async.callWrapper(
            sh,
            rows,
            "noid_egg.deleteIdentifier",
            impl.noid_egg.deleteIdentifier,
            id_str,
        )

    def _batchCreate(self, sh, rows, batch):
        impl.daemon.register_async.callWrapper(
            sh, rows, "noid_egg.batchSetElements", impl.noid_egg.batchSetElements, batch
        )

    def _batchDelete(self, sh, rows, batch):
        impl.daemon.register_async.callWrapper(
            sh,
            rows,
            "noid_egg.batchDeleteIdentifier",
            impl.noid_egg.batchDeleteIdentifier,
            [identifier for identifier, metadata in batch],
        )

    def enqueueIdentifier(self, identifier, operation, blob):
        """Adds an identifier to the binder asynchronous processing queue.

        'identifier' should be the normalized, qualified identifier, e.g.,
        "doi:10.5060/FOO".  'operation' is the identifier operation and
        should be one of the strings "create", "update", or "delete". 'blob'
        is the identifier's metadata dictionary in blob form.
        """
        impl.daemon.register_async.enqueueIdentifier(
            ezidapp.models.binder_queue.BinderQueue, identifier, operation, blob
        )

    def getQueueLength(self):
        """Returns the length of the binder queue."""
        return ezidapp.models.binder_queue.BinderQueue.objects.count()

    _daemonEnabled = [None]
    _threadName = [None]
    _daemonEnabled[0] = (
        django.conf.settings.DAEMON_THREADS_ENABLED
        and django.conf.settings.DAEMONS_BINDER_ENABLED
    )
    if _daemonEnabled[0]:
        # noinspection PyTypeChecker
        _threadName[0] = uuid.uuid1().hex
        impl.daemon.register_async.launch(
            "binder",
            ezidapp.models.binder_queue.BinderQueue,
            _create,
            _update,
            _delete,
            _batchCreate,
            None,
            _batchDelete,
            int(django.conf.settings.DAEMONS_BINDER_NUM_WORKER_THREADS),
            int(django.conf.settings.DAEMONS_BINDER_PROCESSING_IDLE_SLEEP),
            int(django.conf.settings.DAEMONS_BINDER_PROCESSING_ERROR_SLEEP),
            _daemonEnabled,
            _threadName,
        )
