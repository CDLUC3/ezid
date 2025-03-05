#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD
import argparse
import http.client
import logging
import multiprocessing
import os
import signal
import sys
import time
import types
import typing
import urllib.error
import urllib.parse
import urllib.request
import urllib.response

import django.conf
import django.core.management
import django.db
import django.db.transaction

import ezidapp.models.async_queue

class AsyncProcessingCommand(django.core.management.BaseCommand):
    help = __doc__
    setting = None
    queue: typing.Optional[ezidapp.models.async_queue.AsyncQueueBase] = None
    name = None
    _terminated = False
    _last_connection_reset = 0
    _http_client_timeout = 30  # seconds, overridden by DAEMONS_HTTP_CLIENT_TIMEOUT

    class _AbortException(Exception):
        pass

    def __init__(self):
        assert self.setting is not None
        assert self.name is not None
        multiprocessing.current_process().name = self.name
        self.log = logging.getLogger(self.name)
        self.opt = None
        self._last_connection_reset = self.now_int()
        try:
            self._http_client_timeout = django.conf.settings.DAEMONS_HTTP_CLIENT_TIMEOUT
        except AttributeError as e:
            self.log.warning(
                "No settings.DAEMONS_HTTP_CLIENT_TIMEOUT. Using default of %s",
                self._http_client_timeout,
            )
        super().__init__()

    def _handleSignals(self, *args):
        self._terminated = True

    def create_parser(self, *args, **kwargs):
        parser = super().create_parser(*args, **kwargs)
        parser.formatter_class = argparse.RawTextHelpFormatter
        return parser

    def add_arguments(self, parser):
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Debug level logging',
        )

    def handle(self, *args, **opt):
        if django.conf.settings.DEBUG:
            self.log.debug('Testing log level: DEBUG')
            self.log.info('Testing log level: INFO')
            self.log.error('Testing log level: ERROR')
            print('Testing stdout')
            print('Testing stderr', file=sys.stderr)

        # Gracefully handle interrupt or termination
        signal.signal(signal.SIGINT, self._handleSignals)
        signal.signal(signal.SIGTERM, self._handleSignals)

        self.assert_proc_enabled()
        self.opt = types.SimpleNamespace(**opt)
        self.opt.debug |= django.conf.settings.DEBUG

        logging.basicConfig(
            level=logging.DEBUG if self.opt.debug else logging.INFO,
            format='%(levelname)8s %(processName)s %(thread)s: %(message)s',
            stream=sys.stderr,
            force=True,
        )

        # impl.nog.util.log_setup(self.module_name, self.opt.debug)
        # with self.lock:
        self.log.debug('Entering run loop...')
        self.run()

    def run(self):
        """Run async processing loop forever.

        The async processes that don't use a queue based on AsyncQueueBase must override
        this to supply their own loop.

        This method is not called for disabled async processes.
        """
        assert self.queue is not None, "Must specify queue or override run()"

        while not self.terminated():
            qs = self.queue.objects.filter(status=self.queue.UNSUBMITTED,).order_by(
                "-seq"
            )[: django.conf.settings.DAEMONS_MAX_BATCH_SIZE]
            if not qs:
                self.sleep(django.conf.settings.DAEMONS_IDLE_SLEEP)
                continue

            for task_model in qs:
                try:
                    self.do_task(task_model)
                    task_model.status = self.queue.SUCCESS
                except AsyncProcessingIgnored:
                    task_model.status = self.queue.IGNORED
                except Exception as e:
                    if isinstance(e, AsyncProcessingRemoteError):
                        # This is a bit messy. Do not log a trace when the
                        # error is due to the remote service rejecting the request.
                        # Such an error is still permanent for the task though.
                        self.log.error(e)
                    else:
                        self.log.error('#' * 100)
                        self.log.error(f'Exception when handling task "{task_model}"')

                    task_model.error = str(e)
                    # if self.is_permanent_error(e):
                    task_model.status = self.queue.FAILURE
                    task_model.errorIsPermanent = True
                    # raise
                else:
                    task_model.submitTime = self.now_int()

                task_model.save()

            self.sleep(django.conf.settings.DAEMONS_BATCH_SLEEP)
        self.log.info("Exiting run loop.")

    def create(self, task_model):
        """Must be overridden by processes that use the default run loop"""
        raise NotImplementedError()

    def update(self, task_model):
        """Must be overridden by processes that use the default run loop"""
        raise NotImplementedError()

    def delete(self, task_model):
        """Must be overridden by processes that use the default run loop"""
        raise NotImplementedError()

    def assert_proc_enabled(self):
        if not django.conf.settings.DAEMONS_ENABLED:
            self.raise_command_error(f'Cannot start. "DAEMONS_ENABLED" is not True')
        v = getattr(django.conf.settings, self.setting, None)
        if v is None:
            self.raise_command_error(f'Cannot start. "{self.setting}" is missing')
        if v not in (True, False):
            self.raise_command_error(
                f'Cannot start. "{self.setting}" must be a boolean, not {type(self.setting)}'
            )
        if not v:
            self.raise_command_error(f'Cannot start. "{self.setting}" is False')

    def do_task(self, task_model):
        op_label_str = self.queue.OPERATION_CODE_TO_LABEL_DICT[task_model.operation].upper()
        cur_status_str = self.queue.STATUS_CODE_TO_LABEL_DICT[task_model.status]
        self.log.debug(
            'Processing task: {}: {} (current status: {})'.format(
                op_label_str, task_model.refIdentifier.identifier, cur_status_str
            )
        )
        if task_model.operation == self.queue.CREATE:
            return self.create(task_model)
        elif task_model.operation == self.queue.UPDATE:
            return self.update(task_model)
        elif task_model.operation == self.queue.DELETE:
            return self.delete(task_model)
        else:
            raise AssertionError(f'Invalid operation: {task_model.operation}')

    def terminated(self):
        """Return True if the process has been signaled to terminate"""
        return self._terminated

    def is_permanent_error(self, e):
        """Return True if exception appears to be due to a permanent error"""
        # The error is raised from something in a processor
        if isinstance(e, AsyncProcessingError):
            return True
        # We were able to connect to the server, but it returned a 5xx response
        if isinstance(e, urllib.error.HTTPError) and e.code >= 500:
            return True
        # We received an OS level exception that was not urllib HTTP related
        if isinstance(e, OSError) and not isinstance(e, urllib.error.HTTPError):
            return True
        # We received an exception from Python's built-in HTTP client
        if isinstance(e, http.client.HTTPException):
            return True
        return False

    def now(self):
        return time.time()

    def now_int(self):
        '''Seconds since epoch as integer'''
        return int(self.now())

    def sleep(self, duration_sec, check_terminated_sec=1.0):
        """Go to sleep, close DB connection at regular intervals.

        Only reset the db connections after at least this time since last reset.

        Django will automatically reopen database connections as required. Not holding
        on to connections during sleep reduces the number of concurrent connection at
        the cost of having to reestablish the connection when returning from sleep.

        Args:
            duration_sec (float): Total amount of time to sleep. The function will not
              return until this period of time has passed or the process terminate flag
              has been set.
            check_terminated_sec (float): The amount of time to sleep between each check
              of the terminate flag.
        """

        start_ts = time.monotonic()

        if (
            self.now_int() - self._last_connection_reset
            > django.conf.settings.DAEMONS_IDLE_DB_RECONNECT
        ):
            # This log statement can be useful for seeing which async processes were active
            # at a given point in time, but does cause continuous noise in the logs.
            self.log.debug(f'Closing DB connections and sleeping for {duration_sec:.2f}s...')
            django.db.connections["default"].close()
            self._last_connection_reset = self.now_int()

        while time.monotonic() - start_ts < duration_sec and not self.terminated():
            time.sleep(check_terminated_sec)

    def raise_command_error(self, msg_str):
        raise django.core.management.CommandError(
            f'Error: {msg_str}. ' f'Using settings module "{os.environ["DJANGO_SETTINGS_MODULE"]}"'
        )


class AsyncProcessingError(Exception):
    """Raise when a permanent error is encountered."""

    pass


class AsyncProcessingRemoteError(AsyncProcessingError):
    """Permanent error due to a remote service rejecting request"""

    pass


class AsyncProcessingIgnored(Exception):
    """Raise from create/update/delete methods of subclasses when the operation is not
    applicable for the given identifier.

    Create/update/delete tasks are added to all queues for all identifiers. This allows
    logic for deciding if an operation is applicable for a given identifier to be
    encapsulated within the async process which will perform the operation.
    """

    pass
