import contextlib
import logging
import os
import pathlib
import tempfile
import threading
import time

import django.conf
import fasteners

import ezidapp.models.binder_queue
import ezidapp.models.crossref_queue
import ezidapp.models.datacite_queue
import ezidapp.models.registration_queue

log = logging.getLogger(__name__)


def enqueueBinderIdentifier(identifier, operation, blob):
    """Adds an identifier to the binder asynchronous processing queue.

    'identifier' should be the normalized, qualified identifier, e.g.,
    "doi:10.5060/FOO".  'operation' is the identifier operation and
    should be one of the strings "create", "update", or "delete". 'blob'
    is the identifier's metadata dictionary in blob form.
    """
    _enqueueIdentifier(
        ezidapp.models.binder_queue.BinderQueue, identifier, operation, blob
    )


def enqueueCrossRefIdentifier(identifier, operation, metadata, blob):
    """Adds an identifier to the Crossref queue.

    'identifier' should be the normalized, qualified identifier, e.g.,
    "doi:10.5060/FOO". 'operation' is the identifier operation and should
    be one of the strings "create", "update", or "delete".  'metadata' is
    the identifier's metadata dictionary; 'blob' is the same in blob form.
    """
    e = ezidapp.models.crossref_queue.CrossrefQueue(
        identifier=identifier,
        owner=metadata["_o"],
        metadata=blob,
        operation=ezidapp.models.crossref_queue.CrossrefQueue.operationLabelToCode(
            operation
        ),
    )
    e.save()


def enqueueDataCiteIdentifier(identifier, operation, blob):
    """Adds an identifier to the DataCite asynchronous processing queue.

    'identifier' should be the normalized, qualified identifier, e.g.,
    "doi:10.5060/FOO".  'operation' is the identifier operation and
    should be one of the strings "create", "update", or "delete". 'blob'
    is the identifier's metadata dictionary in blob form.
    """
    _enqueueIdentifier(
        ezidapp.models.datacite_queue.DataciteQueue, identifier, operation, blob
    )


def _enqueueIdentifier(model, identifier, operation, blob):
    """Adds an identifier to the asynchronous registration queue named by
    'model'.

    'identifier' should be the normalized, qualified identifier, e.g.,
    "doi:10.5060/FOO".  'operation' is the identifier operation and
    should be one of the strings "create", "update", or "delete".
    'blob' is the identifier's metadata dictionary in blob form.
    """
    e = model(
        enqueueTime=int(time.time()),
        identifier=identifier,
        metadata=blob,
        operation=ezidapp.models.registration_queue.RegistrationQueue.operationLabelToCode(
            operation
        ),
    )
    e.save()


def is_daemon_enabled(setting_name):
    assert isinstance(
        setting_name, str
    ), 'Call with the name of a DAEMONS_*_ENABLED setting, not the value.'
    if not django.conf.settings.DAEMONS_ENABLED:
        return False
    v = getattr(django.conf.settings, setting_name, None)
    assert v is not None, f'Unknown setting: {setting_name}'
    assert v in (
        True,
        False,
    ), f'Setting must be a boolean, not {type(setting_name)}'
    return v


class Lock:
    """Combined thread and process lock.

    Thread locks work by having the threads access the same object in shared
    memory. So it's important that only one lock object object is created for
    each controlled resource.

    Process locks work by having the processes access a named external resource.
    So the lock works regardless of how many lock objects are created, as
    long as they reference the same named resource.
    """

    LOCK_METHOD_DICT = {
        'read': 'read_lock',
        'write': 'write_lock',
    }

    def __init__(self, name):
        self._name = name
        # self.log = log #logging.getLogger(__name__)

        self._temp_dir = tempfile.TemporaryDirectory(prefix='locks')
        # Temp files are created under TemporaryDirectory, which is deleted
        # automatically, So we disable delete on individual files to avoid double
        # delete errors.
        self._lock_file = tempfile.NamedTemporaryFile(
            dir=self._temp_dir.name, delete=False
        )
        self._temp_root_path = pathlib.Path(self._temp_dir.name)
        self._lock_dict = {}
        self._thread_lock = threading.RLock()
        self._process_lock = fasteners.InterProcessLock(self._lock_file.name)

    @contextlib.contextmanager
    def lock_all(self):
        """Lock both threads and processes."""
        with self._thread_lock:
            with self._process_lock:
                yield self

    @contextlib.contextmanager
    def lock(self, lock_name, write=False):
        with self.lock_all():
            if lock_name not in self._lock_dict:
                self._lock_dict[lock_name] = {
                    'thread': {
                        'lock': fasteners.ReaderWriterLock(),
                        'status': None,
                    },
                    'process': {
                        'lock': fasteners.InterProcessReaderWriterLock(
                            self._temp_root_path / lock_name
                        ),
                        'status': None,
                    },
                }

        type_str = 'write' if write else 'read'
        cm_list = [
            self._lock(lock_name, domain_str, type_str)
            for domain_str in ('thread', 'process')
        ]
        es = contextlib.ExitStack()
        [es.enter_context(cm) for cm in cm_list if cm is not None]
        with es:
            yield
        self._dbg(
            'Released locks',
            lock_name=lock_name,
            # domain_str=domain_str,
            type_str=type_str,
        )

    def _lock(self, lock_name, domain_str, type_str):
        lock_dict = self._lock_dict[lock_name]
        dom_dict = lock_dict[domain_str]

        if dom_dict['status'] == type_str:
            self._dbg(
                'Lock already acquired',
                lock_name=lock_name,
                domain_str=domain_str,
                type_str=type_str,
            )
            return None

        dom_dict['status'] = type_str
        lock_obj = dom_dict['lock']

        # Prevent two log lines that are identical except for the 'thread/process'
        # domain str.
        if domain_str == 'thread':
            self._dbg(
                'Waiting for lock',
                lock_name=lock_name,
                domain_str='thread&process',
                type_str=type_str,
            )
        return getattr(lock_obj, self.LOCK_METHOD_DICT[type_str])()

    def _dbg(self, msg_str, **kv):
        log.debug(
            f"name:{self._name}, tid:{threading.get_native_id()}, pid={os.getpid()}, "
            f"{', '.join([f'{k}={v}' for k, v in kv.items()])} - {msg_str}"
        )
