#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

# =============================================================================
#
# EZID :: binder.py
#
# Asynchronous N2T binder processing.
#
#
# -----------------------------------------------------------------------------

import logging

import ezidapp.management.commands.proc_base
import ezidapp.models.async_queue
import impl.log
import impl.nog.util
import impl.noid_egg

log = logging.getLogger(__name__)


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    display = 'Binder'
    name = 'binder'
    setting = 'DAEMONS_BINDER_ENABLED'
    queue = ezidapp.models.async_queue.BinderQueue

    # numWorkerThreads=django.conf.settings.DAEMONS_BINDER_NUM_WORKER_THREADS,
    # idleSleep=django.conf.settings.DAEMONS_BINDER_PROCESSING_IDLE_SLEEP,
    # reattemptDelay=django.conf.settings.DAEMONS_BINDER_PROCESSING_ERROR_SLEEP,

    def __init__(self):
        super().__init__(__name__)

    def add_arguments(self, parser):
        super().add_arguments(parser)

    def create(self, task_model):
        id_str = task_model.refIdentifier.identifier
        metadata = task_model.refIdentifier.metadata
        impl.noid_egg.setElements(id_str, metadata)

    def update(self, task_model):
        id_str = task_model.ref_identifier.identifier

        # TODO: Is this part still required?
        # id_str, metadata = task_model.

        m = impl.noid_egg.getElements(id_str)
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
            impl.noid_egg.setElements(id_str, m)

    def delete(self, id_str, _metadata):
        impl.noid_egg.deleteIdentifier(id_str)

    def batchCreate(self, batch):
        impl.noid_egg.batchSetElements(batch)

    def batchDelete(self, batch):
        impl.noid_egg.batchDeleteIdentifier(
            [identifier for identifier, metadata in batch],
        )
