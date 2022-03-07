#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD
import argparse
import http.client
import logging
import os
import sys
import time
import types
import urllib.error
import urllib.parse
import urllib.request
import urllib.response

import django.conf
import django.core.management
import django.db
import django.db.transaction

import ezidapp.models.async_queue

log = logging.getLogger(__name__)


class AsyncProcessingError(Exception):
    """Raise when a permanent error is encountered."""

    pass

class AsyncProcessingRemoteError(AsyncProcessingError):
    """Permanent error due to a remote service rejecting request"""

    pass



class AsyncProcessingCommand(django.core.management.BaseCommand):
    help = __doc__
    display = None
    setting = None
    queue = None

    class _AbortException(Exception):
        pass

    def __init__(self):
        assert self.display is not None
        assert self.setting is not None
        super().__init__()
        self.opt = None

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
            log.debug('Testing log level: DEBUG')
            log.info('Testing log level: INFO')
            log.error('Testing log level: ERROR')
            print('Testing stdout')
            print('Testing stderr', file=sys.stderr)

        self.assert_proc_enabled()
        self.opt = types.SimpleNamespace(**opt)
        self.opt.debug |= django.conf.settings.DEBUG

        logging.basicConfig(
            level=logging.DEBUG if self.opt.debug else logging.INFO,
            format=(
                f'%(levelname)8s %(name)8s %(module)s %(process)d %(thread)s '
                f'{self.display}: %(message)s'
            ),
            stream=sys.stderr,
            force=True,
        )

        # impl.nog.util.log_setup(self.module_name, self.opt.debug)
        # with self.lock:
        log.debug('Entering run loop...')
        self.run()

    def run(self):
        """Run async processing loop forever.

        The async processes that don't use a queue based on AsyncQueueBase must override
        this to supply their own loop.

        This method is not called for disabled async processes.
        """
        assert self.queue is not None

        while True:
            qs = self.queue.objects.filter(
                status=ezidapp.models.async_queue.AsyncQueueBase.UNSUBMITTED,
            ).order_by("seq")[: django.conf.settings.DAEMONS_MAX_BATCH_SIZE]
            if not qs:
                self.sleep(django.conf.settings.DAEMONS_IDLE_SLEEP)
                continue

            for task_model in qs:
                try:
                    self.do_task(task_model)
                except Exception as e:
                    log.error('#'*100)
                    log.exception(f'Exception when handling task "{task_model}"')
                    task_model.error = str(e)
                    # noinspection PyTypeChecker
                    # if self.is_permanent_error(e):
                    task_model.status = ezidapp.models.async_queue.AsyncQueueBase.FAILURE
                    task_model.errorIsPermanent = True
                    # raise
                else:
                    task_model.status = ezidapp.models.async_queue.AsyncQueueBase.SUBMITTED
                    task_model.submitTime = self.now_int()

                task_model.save()

            self.sleep(django.conf.settings.DAEMONS_BATCH_SLEEP)

            # The previous version of the Crossref process had the following logic,
            # which would delete earlier tasks from the queue if the queue had multiple
            # tasks for the same identifier. We currently have not ported this to Py3
            # because it has the cost of having to check forwards in the queue. The Py2
            # implementation retrieved the full queue, regardless of size, to do these
            # checks. If the situation of having multiple updates for the same
            # identifier in the queue is common enough that it's detrimental to simply
            # process them all, it would be better to check for duplicates when the
            # tasks are being inserted in the queue, and update existing tasks there
            # instead of inserting new ones.
            #
            # if self.queue().objects.filter(identifier=r.identifier).count() > 1:
            #     r.delete()
            #     maxSeq = None
            # else:
            #     if r.status == ezidapp.models.async_queue.CrossrefQueue.UNSUBMITTED:
            #         self._doDeposit(r)
            #         maxSeq = None
            #     elif r.status == ezidapp.models.async_queue.CrossrefQueue.SUBMITTED:
            #         self._doPoll(r)
            #         maxSeq = None
            #     else:
            #         pass

    def create(self, task_model):
        """Overridden by processes that use the default run loop"""
        raise NotImplementedError()

    def update(self, task_model):
        """Overridden by processes that use the default run loop"""
        raise NotImplementedError()

    def delete(self, task_model):
        """Overridden by processes that use the default run loop"""
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
        label_str = ezidapp.models.async_queue.AsyncQueueBase.OPERATION_CODE_TO_LABEL_DICT[
            task_model.operation
        ]
        log.debug(f'Processing task: {label_str}')
        if task_model.operation == ezidapp.models.async_queue.AsyncQueueBase.CREATE:
            self.create(task_model)
        elif task_model.operation == ezidapp.models.async_queue.AsyncQueueBase.UPDATE:
            self.update(task_model)
        elif task_model.operation == ezidapp.models.async_queue.AsyncQueueBase.DELETE:
            self.delete(task_model)
        else:
            raise AssertionError(f'Invalid operation: {task_model.operation}')

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
        return int(self.now())

    def sleep(self, duration_sec):
        """Close DB connections and go to sleep

        Django will automatically reopen database connections as required. Not holding
        on to connections during sleep reduces the number of concurrent connection at
        the cost of having to reestablish the connection when returning from sleep.
        """
        # This log statement can be useful for seeing which async processes were active
        # at a given point in time, but does cause continuous noise in the logs.
        # log.debug(f'Closing DB connections and sleeping for {duration_sec:.2f}s...')
        django.db.connections["default"].close()
        time.sleep(duration_sec)

    def raise_command_error(self, msg_str):
        raise django.core.management.CommandError(
            f'Async process: {self.display}. '
            f'Error: {msg_str}. '
            f'Using settings module "{os.environ["DJANGO_SETTINGS_MODULE"]}"'
        )
