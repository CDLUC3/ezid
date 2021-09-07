"""Display basic statistics for all registered models

This command does not alter any information in the database, and should be safe to run at any time,
including a running production instance.

This command works through the Django ORM and is useful for checking the current state of the
database as seen by the ORM. Information is printed for all models that were discovered in the
model search that Django performs at startup. If any models are missing, it indicates an issue with
the model search.
"""

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import ezidapp.models.identifier
import contextlib
import json
import logging
import pprint
import sys

import django.apps
import django.conf
import django.contrib.auth.models
import django.core.management
import django.db.models
import django.db.transaction
import pymysql.cursors

import ezidapp.models.async_queue
import impl.enqueue
import impl.nog.counter
import impl.nog.tb
import impl.nog.util

log = logging.getLogger(__name__)


class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.opt = None

    def add_arguments(self, parser):
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Debug level logging',
        )

    def handle(self, *_, **opt):
        db = ORMStats()
        db.print_all()
        # db.print_identifier('ark:/13030/c80c4tkc')
        # db.print_identifier('ark:/13030/c8028pmk')


class ORMStats:

    def __init__(self):
        self.exit_stack = contextlib.ExitStack()
        self.counter = self.exit_stack.enter_context(impl.nog.counter.Counter())
        self.page_size = django.conf.settings.QUERY_PAGE_SIZE

    def print_identifier(self, identifier):
        id_model = ezidapp.models.identifier.Identifier.objects.filter(
            identifier=identifier).get()
        # print(id_model)
        # pprint.pp(id_model.cm)

        print('-' * 100)

        impl.enqueue.enqueueBinderIdentifier(
            identifier=id_model.identifier,
            operation='update',
            blob={'x': 'y'},
        )

        # impl.nog.util.print_table(row_list, log.info)

    def print_all(self):
        # row_list = []
        row_list = [('MODEL', 'TABLE', 'ROWS')]
        for m in django.apps.apps.get_models(
                include_auto_created=True, include_swapped=True
        ):
            row_list.append(
                (
                    m._meta.label,
                    m._meta.db_table,
                    m.objects.count(),
                    # ','.join(s.name for s in m._meta.fields),
                )
            )
        impl.nog.util.print_table(row_list, log.info)
