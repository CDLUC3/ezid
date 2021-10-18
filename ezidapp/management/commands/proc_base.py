#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import abc
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


class AsyncProcessingCommand(abc.ABC, django.core.management.BaseCommand):
    help = __doc__
    setting = None
    name = None
    queue = None

    class _AbortException(Exception):
        pass

    def __init__(self):
        super().__init__()
        self.opt = None
        self.is_debug = None

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
        if django.conf.settings.DEBUG:
            log.debug('Testing log level: DEBUG')
            log.info('Testing log level: INFO')
            log.error('Testing log level: ERROR')
            print('Testing stdout')
            print('Testing stderr', file=sys.stderr)

        self.assert_proc_enabled()
        self.opt = types.SimpleNamespace(**opt)
        self.is_debug = self.opt.debug

        # impl.nog.util.log_setup(self.module_name, self.opt.debug)

        # with self.lock:
        self.run()

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

    def run(self):
        """Run async processing loop forever"""
        while True:
            qs = self.queue.objects.filter(
                status=ezidapp.models.async_queue.AsyncQueueBase.UNSUBMITTED,
            ).order_by("seq")[
                : django.conf.settings.MAX_BATCH_SIZE
            ]
            if not qs:
                # django.db.connections["default"].close()
                time.sleep(django.conf.settings.DAEMONS_BINDER_PROCESSING_IDLE_SLEEP)
                continue

            for task_model in qs:
                try:
                    self.do_task(task_model)
                except Exception as e:
                    log.exception('Task registration error')
                    task_model.error = str(e)
                    if self.is_permanent_error(e):
                        task_model.status = ezidapp.models.async_queue.AsyncQueueBase.FAILURE,
                        task_model.errorIsPermanent = True
                        # raise
                else:
                    task_model.status = ezidapp.models.async_queue.AsyncQueueBase.SUBMITTED
                    task_model.submitTime = self.now_int()

                task_model.save()

    def do_task(self, task_model):
        label_str = ezidapp.models.async_queue.AsyncQueueBase.OPERATION_CODE_TO_LABEL_DICT[
            task_model.operation
        ]
        log.debug(self.fmt_msg(f'Processing task: {label_str}'))
        if task_model.operation == ezidapp.models.async_queue.AsyncQueueBase.CREATE:
            self.create(task_model)
        elif task_model.operation == ezidapp.models.async_queue.AsyncQueueBase.UPDATE:
            self.update(task_model)
        elif task_model.operation == ezidapp.models.async_queue.AsyncQueueBase.DELETE:
            self.delete(task_model)
        else:
            raise AssertionError(f'Invalid operation: {task_model.operation}')

    # def sleep(self, duration=None):
    #     django.db.connections["default"].close()
    #     time.sleep(duration or self.state.idleSleep)

    def is_permanent_error(self, e):
        """Return True if exception appears to be due to a permanent error"""
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

    @staticmethod
    def now():
        return time.time()

    @staticmethod
    def now_int():
        return int(AsyncProcessingCommand.now())

    def raise_command_error(self, msg_str):
        raise django.core.management.CommandError(
            self.fmt_msg(
                f'Error: {msg_str}). '
                f'Using settings module "{os.environ["DJANGO_SETTINGS_MODULE"]}"'
            )
        )

    def create(self, task_model):
        raise NotImplementedError()

    def update(self, task_model):
        raise NotImplementedError()

    def delete(self, task_model):
        raise NotImplementedError()

    def fmt_msg(self, fmt_str: str, *a, **kw):
        return f'Async process {self.name}: {fmt_str.format(*a, **kw)}'
