# =============================================================================
#
# EZID :: binder.py
#
# Asynchronous N2T binder processing.
#
# License:
#   Copyright (c) 2017, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import logging

import django.conf

import ezidapp.management.commands.proc_base
import ezidapp.models.registration_queue
import impl.log
import impl.nog.util
import impl.noid_egg

log = logging.getLogger(__name__)


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    display = 'Binder'
    name = 'binder'
    setting = 'DAEMONS_BINDER_ENABLED'

    def __init__(self):
        super().__init__(
            __name__,
            registrar="binder",
            queueModel=ezidapp.models.registration_queue.BinderQueue,
            createFunction=self._create,
            updateFunction=self._update,
            deleteFunction=self._delete,
            batchCreateFunction=self._batchCreate,
            batchUpdateFunction=None,
            batchDeleteFunction=self._batchDelete,
            numWorkerThreads=django.conf.settings.DAEMONS_BINDER_NUM_WORKER_THREADS,
            idleSleep=django.conf.settings.DAEMONS_BINDER_PROCESSING_IDLE_SLEEP,
            reattemptDelay=django.conf.settings.DAEMONS_BINDER_PROCESSING_ERROR_SLEEP,
        )

    def add_arguments(self, parser):
        """
        Args:
            parser:
        """
        super().add_arguments(parser)

    def handle_daemon(self, args):
        """
        Args:
            args:
        """
        super().run()

    def _create(self, rows, id_str, metadata):
        """
        Args:
            rows:
            id_str:
            metadata:
        """
        self.callWrapper(
            rows,
            "noid_egg.setElements",
            impl.noid_egg.setElements,
            id_str,
            metadata,
        )

    def _update(self, rows, id_str, metadata):
        """
        Args:
            rows:
            id_str:
            metadata:
        """
        m = self.callWrapper(
            rows, "noid_egg.getElements", impl.noid_egg.getElements, id_str
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
            self.callWrapper(
                rows, "noid_egg.setElements", impl.noid_egg.setElements, id_str, m
            )

    def _delete(self, rows, id_str, _metadata):
        """
        Args:
            rows:
            id_str:
            _metadata:
        """
        self.callWrapper(
            rows,
            "noid_egg.deleteIdentifier",
            impl.noid_egg.deleteIdentifier,
            id_str,
        )

    def _batchCreate(self, rows, batch):
        """
        Args:
            rows:
            batch:
        """
        self.callWrapper(
            rows, "noid_egg.batchSetElements", impl.noid_egg.batchSetElements, batch
        )

    def _batchDelete(self, rows, batch):
        """
        Args:
            rows:
            batch:
        """
        self.callWrapper(
            rows,
            "noid_egg.batchDeleteIdentifier",
            impl.noid_egg.batchDeleteIdentifier,
            [identifier for identifier, metadata in batch],
        )
