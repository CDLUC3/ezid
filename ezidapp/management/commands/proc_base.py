import contextlib
import http.client
import logging
import os
import pprint
import random
import sys
import threading
import time
import types
import urllib.error
import urllib.parse
import urllib.request
import urllib.response

import django.conf
import django.db
import django.db.transaction

import impl.daemon
import impl.log
import impl.nog.util
import impl.util

log = logging.getLogger(__name__)

import django.core.management

"""
Queue tables:

ezidapp_binderqueue
ezidapp_crossrefqueue
ezidapp_datacitequeue
ezidapp_downloadqueue
ezidapp_updatequeue       

"""


class AsyncProcessingCommand(django.core.management.BaseCommand):
    help = __doc__
    setting = None
    name = None

    # queue_model = None

    class _AbortException(Exception):
        pass

    def __init__(self, module_name, **state):
        super().__init__()
        global log
        self.state = types.SimpleNamespace(**state)
        # self.state = types.SimpleNamespace(
        #     registrar=None,
        #     queueModel=None,
        #     createFunction=None,
        #     updateFunction=None,
        #     deleteFunction=None,
        #     batchCreateFunction=None,
        #     batchUpdateFunction=None,
        #     batchDeleteFunction=None,
        #     idleSleep=None,
        #     reattemptDelay=None,
        #     threadNameHolder=None,
        # )
        self.module_name = module_name
        self.lock = threading.RLock()  # impl.daemon.Lock(self.setting.lower())
        self.log = logging.getLogger(self.module_name)
        log = self.log

        # noinspection PyArgumentList
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(levelname)8s %(name)8s %(module)s %(process)d %(thread)s %(message)s',
            stream=sys.stderr,
            force=True,
        )

    def add_arguments(self, parser):
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Debug level logging',
        )

    def handle(self, *args, **opt):
        log.debug('Testing log level: DEBUG')
        log.info('Testing log level: INFO')
        log.error('Testing log level: ERROR')
        print('Testing stdout')
        print('Testing stderr', file=sys.stderr)

        if not impl.daemon.is_daemon_enabled(self.setting):
            raise django.core.management.CommandError(
                f'The {self.display, } daemon is not currently enabled and cannot be started. '
                f'To start this daemon, ensure that both '
                f'"DAEMONS_ENABLED" and "{self.setting}" '
                f'are set to True in {os.environ["DJANGO_SETTINGS_MODULE"]}.'
            )

        self.opt = types.SimpleNamespace(**opt)
        self.is_debug = self.opt.debug
        impl.nog.util.log_setup(self.module_name, self.opt.debug)
        # with self.lock.lock(self.name, write=True):
        with self.lock:
            return self.handle_daemon(self.opt)

    def run(self):
        self._sleep()
        while True:
            try:
                while True:
                    n = self._loadRows()
                    if n > 0:
                        break
                    self._sleep()
                while self._loadedRowsLength() > 0:
                    self._sleep()
            # except _AbortException:
            #     break
            except Exception as e:
                self.otherError("register_async.run/" + self.state.registrar, e)
                self._sleep()

    def callWrapper(self, rows, methodName, function, *args):
        """This function should be used by registrars to wrap calls to registrar-
        specific create/update/delete functions.

        It hides all transient errors (by retrying indefinitely) and raises
        all others. 'sh' and 'rows' are supplied by this module and should
        simply be passed through.  'function' is the function to call;
        'methodName' is its name for error reporting purposes.  Any
        additional arguments are passed through to 'function'.
        """
        log.debug(
            pprint.pformat(
                dict(
                    callWrapper=self,
                    rows=rows,
                    methodName=methodName,
                    function=function,
                    args=args,
                )
            )
        )
        while True:
            try:
                # r = function(*args)
                breakpoint()
                log.debug(f'Returning: {r}')
                return r
            except Exception as e:
                if (
                    (isinstance(e, urllib.error.HTTPError) and e.code >= 500)
                    or (
                        isinstance(e, IOError)
                        and not isinstance(e, urllib.error.HTTPError)
                    )
                    or isinstance(e, http.client.HTTPException)
                ):
                    for r in rows:
                        r.error = impl.util.formatException(e)
                    with django.db.transaction.atomic():
                        for r in rows:
                            r.save()
                    self._sleep(self.state.reattemptDelay)
                else:
                    raise Exception(
                        f"{methodName} error: {impl.util.formatException(e)}"
                    )

    @staticmethod
    def launch(
        self,
        registrar,
        queueModel,
        createFunction,
        updateFunction,
        deleteFunction,
        batchCreateFunction,
        batchUpdateFunction,
        batchDeleteFunction,
        numWorkerThreads,
        idleSleep,
        reattemptDelay,
        # threadNameHolder,
    ):
        """Launches a registration thread (and subservient Worker threads).

        Args:
            self:
            registrar:
                The registrar the thread is for, e.g., "datacite"
            queueModel:
                Is the registrar's queue database model, e.g.,
                ezidapp.models.registration_queue.DataciteQueue.
            createFunction:
            updateFunction:
            deleteFunction:
                The registrar-specific functions to be called.  Each should accept arguments (sh,
                rows, identifier, metadata) where 'identifier' is a normalized, qualified
                identifier, e.g., "doi:10.5060/FOO", and 'metadata' is the identifier's metadata
                dictionary.  Each function should wrap external HTTP calls using 'callWrapper'
                above, passing through the 'sh' and 'rows' arguments.
            batchCreateFunction:
            batchUpdateFunction:
            batchDeleteFunction:
                The 'batch*' functions are similar to the create/update/delete functions. If not
                none, each should process multiple identifiers and accept arguments (sh, row, batch)
                where 'batch' is a list of (identifier, metadata dictionary) tuples.
            numWorkerThreads:
            idleSleep:
            reattemptDelay:

        No longer used:
        'enabledFlagHolder' is a singleton list containing a boolean flag that indicates if the thread is enabled.
        'threadNameHolder' is a singleton list containing the string name of the current thread.
        """
        # name = threadNameHolder[0]
        t = threading.Thread(target=lambda: self.run(), name=self.name)

        for i in range(numWorkerThreads):
            t = threading.Thread(
                target=lambda: self._workerThread(), name=f"{self.name}.{i:d}"
            )

    def _sleep(self, duration=None):
        django.db.connections["default"].close()
        time.sleep(duration or self.state.idleSleep)

    def _queue(self):
        return self.state.queueModel

    @contextlib.contextmanager
    def _lockLoadedRows(self):
        # Decorator.  Assumes the state holder is the first argument to the
        # decorated function.
        def wrapped(f, *args, **kwargs):
            self.state.lock.acquire()
            try:
                r = f(*args, **kwargs)
                log.debug(f'{f}({args} {kwargs.items()}) -> {r}')
                return r
            finally:
                self.state.lock.release()

        return wrapped

    @_lockLoadedRows
    def _loadedRowsLength(self):
        return len(self.state.loadedRows)

    @_lockLoadedRows
    def _setLoadedRows(self, rows):
        self.state.loadedRows = rows

    @_lockLoadedRows
    def _deleteLoadedRows(self, rows):
        seqs = set(r.seq for r in rows)
        for i in range(len(self.state.loadedRows) - 1, -1, -1):
            if self.state.loadedRows[i].seq in seqs:
                del self.state.loadedRows[i]

    @_lockLoadedRows
    def _nextUnprocessedLoadedRows(self):
        rows = []
        for r in self.state.loadedRows:
            if not hasattr(r, "beingProcessed"):
                # We'll always return one row, if one can be found.  Multiple
                # rows will be returned only if they share the same operation
                # and the registrar supports the corresponding batch function.
                if len(rows) == 0:
                    r.beingProcessed = True
                    rows.append(r)
                    if self.state.functions["batch"][r.operation] is None:
                        break
                else:
                    if r.operation == rows[0].operation:
                        r.beingProcessed = True
                        rows.append(r)
        return rows

    def _loadRows(self, limit=1000):
        qs = self._queue().objects.all().order_by("seq")[:limit]
        seen = set()
        rows = []
        for r in qs:
            if r.identifier not in seen:
                if not r.errorIsPermanent:
                    rows.append(r)
                seen.add(r.identifier)
        if len(rows) == 0 and len(qs) == limit:
            # Incredibly unlikely, but just in case: if our query returned a
            # full set of rows but we ended up selecting none (because they
            # all had permanent errors or are duplicates), try increasing the
            # limit.  In the limiting case, the entire table will be returned.
            return self._loadRows(limit * 2)
        n = len(rows)
        self._setLoadedRows(rows)
        return n

    def _workerThread(self):
        # Sleep between 1x and 2x the idle sleep, to give the main daemon a
        # chance to load the row cache and to prevent the workers from
        # running synchronously.
        time.sleep(self.state.idleSleep * (random.random() + 1))
        while True:
            log.debug('_workerThread TOP')
            try:
                while True:
                    rows = self._nextUnprocessedLoadedRows()
                    if len(rows) > 0:
                        break
                    self._sleep()
                try:
                    if len(rows) == 1:
                        f = self.state.functions["single"][rows[0].operation]
                        f(
                            # self, # TODO
                            rows,
                            rows[0].identifier,
                            impl.util.deblobify(rows[0].metadata),
                        )
                    else:
                        f = self.state.functions["batch"][rows[0].operation]
                        f(
                            # sh,
                            # self, # TODO
                            rows,
                            [
                                (r.identifier, impl.util.deblobify(r.metadata))
                                for r in rows
                            ],
                        )
                except Exception as e:
                    # N.B.: on the assumption that the registrar-specific function
                    # used callWrapper defined above, the error can only be
                    # permanent.
                    for r in rows:
                        r.error = impl.util.formatException(e)
                        r.errorIsPermanent = True
                    with django.db.transaction.atomic():
                        for r in rows:
                            r.save()
                    self.otherError(
                        "register_async._workerThread/" + self.state.registrar, e
                    )
                else:
                    with django.db.transaction.atomic():
                        for r in rows:
                            # Django "helpfully" sets seq, the primary key, to None
                            # after deleting a row.  But we need the seq value to
                            # delete the row out of self.state.loadedRows, ergo...
                            t = r.seq
                            r.delete()
                            r.seq = t
                finally:
                    self._deleteLoadedRows(rows)
            except Exception as e:
                self.otherError(
                    "register_async._workerThread/" + self.state.registrar, e
                )
                self._sleep()

    def otherError(*a, **kw):
        log.error(f'otherError: {a} {kw}')
        return impl.log.otherError(*a, **kw)

    @staticmethod
    def now():
        return time.time()

    @staticmethod
    def nowi():
        return int(AsyncProcessingCommand.now())
