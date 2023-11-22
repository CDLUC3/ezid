#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Asynchronous N2T binder processing
"""

import logging

import ezidapp.management.commands.proc_base
import ezidapp.models.async_queue
import ezidapp.models.identifier
import impl.log
import impl.noid_egg

log = logging.getLogger(__name__)


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    name = __name__
    setting = 'DAEMONS_BINDER_ENABLED'
    queue = ezidapp.models.async_queue.BinderQueue

    def create(self, task_model: ezidapp.models.async_queue.BinderQueue):
        """
        Creates an entry in N2T for a new identifier.
        The fields to be set are described in the N2T API documentation:
          http://n2t.net/e/n2t_apidoc.html
        Minimally, the fields must include:
          who
          what
          when
          where
          how    Where is this value stored in EZID?
          _t
        """
        id_str = task_model.refIdentifier.identifier
        self.log.info("CREATE: %s", id_str)
        ##metadata = task_model.refIdentifier.metadata
        # add the required target metadata:
        ##metadata["_t"] = task_model.refIdentifier.target
        metadata = task_model.refIdentifier.toLegacy()
        try:
            impl.noid_egg.setElements(id_str, metadata)
            task_model.status = self.queue.SUCCESS
        except AssertionError as e:
            task_model.status = self.queue.FAILURE
            self.log.error("CREATE: %s", id_str, e)
        except Exception as e:
            task_model.status = self.queue.FAILURE
            self.log.error("CREATE: %s", id_str, e)
        task_model.save()

    def update(self, task_model: ezidapp.models.async_queue.BinderQueue):
        '''
        task_model: BinderQueue

        Retrieves existing metadata from N2T and sends back updates to any
        new fields oor fields that have changed values.
        '''
        id_str = task_model.refIdentifier.identifier
        ##metadata = task_model.refIdentifier.metadata
        ### add the required target metadata:
        ##metadata["_t"] = task_model.refIdentifier.target
        metadata = task_model.refIdentifier.toLegacy()
        self.log.info("UPDATE: %s", id_str)

        # Retrieve the existing metadata from N2T
        m = impl.noid_egg.getElements(id_str)
        if m is None:
            m = {}
        # First, update m with provided metadata
        for k, v in list(metadata.items()):
            # If the provided metadata matches existing, then ignore
            if m.get(k) == v:
                del m[k]
            # Otherwise add property to list for sending back to N2T
            else:
                m[k] = v
        # If properties retrieved from N2T are not present in the supplied
        # update metadata, then set the value of the field to an empty string.
        # An empty value results in an "rm" (remove) operation for that field
        # being sent to N2T.
        for k in list(m.keys()):
            if k not in metadata:
                m[k] = ""
        self.log.debug("UPDATE: %s m = %s", id_str, m)
        if len(m) > 0:
            try:
                impl.noid_egg.setElements(id_str, m)
                task_model.status = self.queue.SUCCESS
            except AssertionError as e:
                task_model.status = self.queue.FAILURE
                self.log.error("UPDATE: %s", id_str, e)
            except Exception as e:
                task_model.status = self.queue.FAILURE
                self.log.error("UPDATE: %s", id_str, e)
        task_model.save()

    def delete(self, task_model: ezidapp.models.async_queue.BinderQueue):
        id_str = task_model.refIdentifier.identifier
        try:
            impl.noid_egg.deleteIdentifier(id_str)
            task_model.status = self.queue.SUCCESS
        except AssertionError as e:
            task_model.status = self.queue.FAILURE
            self.log.error("DELETE: %s", id_str, e)
        except Exception as e:
            task_model.status = self.queue.FAILURE
            self.log.error("DELETE: %s", id_str, e)
        task_model.save()

    def batchCreate(self, batch):
        impl.noid_egg.batchSetElements(batch)

    def batchDelete(self, batch):
        impl.noid_egg.batchDeleteIdentifier(
            [identifier for identifier, metadata in batch],
        )
