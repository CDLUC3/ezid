"""A simple name based lock and key/value store that can be shared safely between an
arbitrary number of possibly unrelated processes and threads.

- Both key and value must be a 32-bit integer. Keys are intended to be database row
IDs and values will most likely be counters.
- Does not require the processes to be children of the same parent, which is the case
for the standard Python multiprocessing library.
- Names can be selected to support an optimal locking granularity.
"""
#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import contextlib
import itertools
import logging
import mmap
import os
import pathlib
import pprint
import struct
import tempfile
import threading
import time

import fasteners

log = logging.getLogger(__name__)

# We match the database, which stores user ids as 32-bit ints.
INT_SIZE = 4
INT_SIZE_FMT = 'i'
assert struct.calcsize(INT_SIZE_FMT) == INT_SIZE

LOCK_ROOT = pathlib.Path(tempfile.gettempdir(), "DEX-LOCK")
LOCK_ROOT.mkdir(0o755, parents=True, exist_ok=True)


class NamedThreadLocks:
    """Wrap threading.RLock to provide reentrant and named thread locks."""

    def __init__(self):
        self.locks = {}
        self.mylock = threading.RLock()
        self.es = contextlib.ExitStack()
        self.out = pathlib.Path('/tmp/named_thread_locks.log').open('w')

    @contextlib.contextmanager
    def __call__(self, name):
        with self.mylock:
            self.locks.setdefault(name, threading.RLock())
        ts = time.time()
        self.p(f'{name}: waiting')
        with self.locks[name]:
            acq_ts = time.time() - ts
            self.p(f'{name}: acquired after {acq_ts :.2f}s')
            yield name
        release_ts = time.time() - ts
        self.p(f'{name}: released after {release_ts - acq_ts :.2f}s')

    def p(self, *a, **kw):
        print(*a, **kw, file=self.out)


class CombinedLock:
    """Combined thread and process lock

    Thread locks work by having the threads access the same object in shared memory. So it's
    important that only one lock object is created for each shared resource.

    Process locks work by having the processes access a named external resource. So the lock works
    regardless of how many lock objects are created, as long as they reference the same named
    resource.
    """
    _named_thread_lock = NamedThreadLocks()
    _proc_dict = {}

    def __init__(self, root_path=None):
        root_path = root_path or tempfile.gettempdir()
        self._root_path = pathlib.Path(root_path)
        self._named_thread_lock = NamedThreadLocks()
        self._proc_dict = {}

    @contextlib.contextmanager
    def lock(self, lock_name, is_write):
        # log.error(f'{self._root_path}, {lock_name}, {is_write}')
        with contextlib.ExitStack() as es:
            thread_lock_name = f'{self._root_path / lock_name}_t'
            process_lock_name = f'{self._root_path / lock_name}_p'
            # InterProcessReaderWriterLock is reentrant.
            p = self._proc_dict.setdefault(
                process_lock_name,
                fasteners.InterProcessReaderWriterLock(self._root_path / lock_name),
            )
            with es:
                es.enter_context(self._named_thread_lock(lock_name))
                es.enter_context(
                    getattr(p, 'write_lock' if is_write else 'read_lock')()
                )
                yield es


# class TmpFile:
#     """Generate temporary pathlib.Paths below a temporary folder.
#
#     # >>> with TmpFile() as f:
#     # >>>   f.write_text('abc')
#     # >>>   ...
#     # >>>   new_f = f.new()
#     # >>>   f.write_text('xyz')
#     # >>>
#     # >>>   assert f.read_text() == 'abc'
#     # >>>   assert new_f.read_text() == 'xyz'
#     # >>>
#     # >>> assert not f.exists()
#     # >>> assert not new_f.exists()
#     # >>>
#     """
#
#     def __init__(self, prefix=''):
#         self.prefix = prefix
#         self._es = contextlib.ExitStack()
#
#     def __enter__(self):
#         self._temp_dir = self._es.enter_context(tempfile.TemporaryDirectory(self._prefix))
#         return self
#
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         self._es.close()
#
#     # Temp files are created under TemporaryDirectory, which is deleted
#     # automatically, So we disable delete on individual files to avoid double
#     # delete errors.
#     def new(self):
#         return tempfile.NamedTemporaryFile(dir=self._temp_dir.name, delete=False)
#
#     def _dbg(self, msg_str, **kv):
#         log.debug(f'- {msg_str}')
#         log.debug(
#             f"name:{self._prefix}, tid:{threading.get_native_id()}, pid={os.getpid()}"
#         )
#         list(map(log.debug, [f'  {k}={v}' for k, v in kv.items()]))


# class TmpFile:
#     def __init__(self, prefix=None):
#         self._prefix = prefix or TmpFile()
#         self._es = contextlib.ExitStack()
#
#     def __call__(self):
#
#
#     def __enter__(self):
#         self._temp_dir = self._es.enter_context(
#             tempfile.TemporaryDirectory(self._prefix)
#         )
#
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         self._es.close()
#
#     # Temp files are created under TemporaryDirectory, which is deleted
#     # automatically, So we disable delete on individual files to avoid double
#     # delete errors.
#     def new_path(self):
#         return tempfile.NamedTemporaryFile(dir=self._temp_dir.name, delete=False)


class MemMapDict:
    # Lock for initializing the classes only once per process.
    _combined_lock = CombinedLock()
    is_init = False
    @fasteners.interprocess_write_locked('../impl/init')
    def __init__(self, dict_name, max_items, item_fmt, root_path=None):
        with self._combined_lock.lock('_mem_map_init', is_write=True):
            if self.is_init:
                return
            self.is_init = True
            self._es = contextlib.ExitStack()
            #self._es.enter_context(TmpFile())
            # self._root_path = pathlib.Path(tempfile.mkdtemp()
            self._root_path = pathlib.Path(
                root_path if root_path else tempfile.gettempdir()
            )

            self._dict_name = dict_name
            self._max_items = max_items
            self._item_fmt = item_fmt

            self._dict_path = self._root_path / dict_name
            self._map_path = self._dict_path / 'map'

            self._dict_path.mkdir(parents=True, exist_ok=True)

            self._item_size = struct.calcsize(item_fmt)
            self._fmt = item_fmt
            self._size = max_items * self._item_size * 2 + self._item_size
            self._buf = bytearray(self._size)

            self._map_es = contextlib.ExitStack()
            self._lock_es = contextlib.ExitStack()

            # self._base_lock = Lock(self._root_path)

            self._prep_mm_file()
            self._map_mm_file()

        # self._dump_state()

    @fasteners.interprocess_write_locked('../impl/init')
    def __enter__(self):
        self._combined_lock.lock('mm_dict', is_write=True)
        # self._dump_state()
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        self._lock_es.close()


    # def __del__(self):
    #     if getattr(self, '_map_es', None) is not None:
    #         self._map_es.close()

    fasteners.interprocess_write_locked('/tmp/another')

    @fasteners.interprocess_write_locked('../impl/init')
    def adjust(self, rid, delta_int):
        with self._combined_lock.lock('mm_dict', is_write=True):
            d = self._read_dict()
            d.setdefault(rid, 0)
            d[rid] += 1
            self._write_dict(d)


    # fasteners.interprocess_write_locked('/tmp/another2')

    @fasteners.interprocess_write_locked('../impl/init')
    def get(self, rid, default=0):
        with self._combined_lock.lock('mm_dict', is_write=False):
            d = self._read_dict()
            return d.get(rid, default)


    def _prep_mm_file(self):
        if self._map_path.exists():
            assert self._map_path.stat().st_size >= self._size
        else:
            with self._map_path.open('wb') as f:
                f.write(self._buf)


    def _map_mm_file(self):
        self._file_obj = self._map_es.enter_context(open(self._map_path, mode="r+"))
        self._mmap_obj = self._map_es.enter_context(
            mmap.mmap(self._file_obj.fileno(), length=0, access=mmap.ACCESS_WRITE)
        )


    # def __call__(self, write):
    #     self._is_write = write
    #     return self

    def _dump_state(self):
        self._dbg(
            'state',
            cls=self.__class__.__name__,
            root_path=self._root_path,
            map_path=self._map_path,
            max_items=self._max_items,
            item_fmt=self._item_fmt,
            lock=self._combined_lock,
            item_size=self._item_size,
            fmt=self._fmt,
            size=self._size,
        )


    def _read_dict(self):
        self._buf = self._read(0, self._size)
        r = struct.unpack('i' + 'ii' * self._max_items, self._buf)
        kv_list = zip(r[1::2], r[2::2])
        d = dict(kv_list)
        return d


    def _write_dict(self, d):
        flat = itertools.chain.from_iterable(d.items())
        struct.pack_into('i' + 'ii' * len(d), self._mmap_obj, 0, len(d), *flat)
        self._mmap_obj.flush()


    # Start of interface with per-item lock granularity.
    # def read_s32(self, idx):
    #     # https://docs.python.org/3.8/library/struct.html#struct.calcsize
    #     # l = long
    #     size = struct.calcsize('i')
    #     return struct.unpack('l', self.read(idx * size, size))
    #
    # def write_s32(self, idx, n):
    #     self.write(idx * size, struct.pack('i', n))

    def _read(self, offset, size):
        # self._dbg('_read', offset=offset, len_bytes=len(bytes))
        return self._mmap_obj[offset: offset + size]


    def _write(self, offset, bytes):
        # log.debug(f'_write', offset=offset, len_bytes=len(bytes))
        self._mmap_obj[offset: offset + len(bytes)] = bytes
        self._mmap_obj.flush()


    # @impl.log.stacklog
    def _dbg(self, msg_str, **kv):
        log.debug(f'- {msg_str}')
        log.debug(
            f"name:{self._root_path}, tid:{threading.get_native_id()}, pid={os.getpid()}"
        )
        list(map(log.debug, [f'  {k}={v}' for k, v in kv.items()]))
