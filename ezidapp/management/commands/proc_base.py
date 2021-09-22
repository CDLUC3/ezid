#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import abc
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

import impl.enqueue
import impl.log
import impl.nog.util
import impl.util
import ezidapp.models.async_queue

import django.core.management

import settings.test_settings

log = logging.getLogger(__name__)

"""
Queue tables:

ezidapp_binderqueue
ezidapp_crossrefqueue
ezidapp_datacitequeue
ezidapp_downloadqueue
ezidapp_updatequeue       

"""


class AsyncProcessingCommand(abc.ABC, django.core.management.BaseCommand):
    help = __doc__
    setting = None
    name = None

    # queue_model = None

    class _AbortException(Exception):
        pass

    def __init__(self, module_name):
        super().__init__()

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

        self.assert_daemon_enabled()

        self.opt = types.SimpleNamespace(**opt)
        self.is_debug = self.opt.debug
        # impl.nog.util.log_setup(self.module_name, self.opt.debug)

        # with self.lock:
        self.run()

    def assert_daemon_enabled(self):
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
            qs = self.queue.objects.filter(errorIsPermanent=False).order_by("seq")[
                : django.conf.settings.MAX_BATCH_SIZE
            ]
            if not qs:
                # django.db.connections["default"].close()
                time.sleep(django.conf.settings.DAEMONS_BINDER_PROCESSING_IDLE_SLEEP)
                continue

            for task in qs:
                if task.operation == ezidapp.models.async_queue.AsyncQueueBase.CREATE:
                    self.create(task)
                elif task.operation == ezidapp.models.async_queue.AsyncQueueBase.UPDATE:
                    self.update(task)
                elif task.operation == ezidapp.models.async_queue.AsyncQueueBase.DELETE:
                    self.delete(task)
                else:
                    self.raise_command_error(self, f'Invalid operation: {task.operation}')

            for row in self.queue.objects.all().order_by("seq")[
                : django.conf.settings.MAX_BATCH_SIZE
            ]:
                pass

    def callWrapper(self, task, function, *args):
        """This function should be used by registrars to wrap calls to registrar-
        specific create/update/delete functions.

        It hides all transient errors (by retrying indefinitely) and raises
        all others. 'sh' and 'task' are supplied by this module and should
        simply be passed through.  'function' is the function to call;
        'methodName' is its name for error reporting purposes.  Any
        additional arguments are passed through to 'function'.
        """
        log.debug(
            pprint.pformat(
                dict(
                    callWrapper=self,
                    task=task,
                    function=function,
                    args=args,
                )
            )
        )
        try:
            r = function(*args)
            # breakpoint()
            log.debug(f'Returning: {r}')
        except Exception as e:
            task.error = impl.util.formatException(e)
            if self.is_permanent_error(e):
                task.errorIsPermanent = True
        else:
            task.error = 'Successful'

        task.save()

    # def sleep(self, duration=None):
    #     django.db.connections["default"].close()
    #     time.sleep(duration or self.state.idleSleep)

    def is_permanent_error(self, e):
        """Return True if exception appears to be due to a permanent error"""
        return (
            (isinstance(e, urllib.error.HTTPError) and e.code >= 500)
            or (isinstance(e, IOError) and not isinstance(e, urllib.error.HTTPError))
            or isinstance(e, http.client.HTTPException)
        )

    @staticmethod
    def now():
        return time.time()

    @staticmethod
    def nowi():
        return int(AsyncProcessingCommand.now())

    def raise_command_error(self, msg_str):
        raise django.core.management.CommandError(
            f'Async process {self.name} error: {msg_str}). '
            f'Using settings module "{os.environ["DJANGO_SETTINGS_MODULE"]}'
        )

    def create(self, task):
        raise NotImplementedError()

    def update(self, task):
        raise NotImplementedError()

    def delete(self, task):
        raise NotImplementedError()
