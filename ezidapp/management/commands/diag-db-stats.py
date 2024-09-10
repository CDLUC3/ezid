#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Display basic statistics for all registered models

This command does not alter any information in the database, and should be safe to run
at any time, including a running production instance.

This command works through the Django ORM and is useful for checking the current state
of the database as seen by the ORM. Information is printed for all models that were
discovered in the model search that Django performs at startup. If any models are
missing, it indicates an issue with the model search.
"""

import contextlib
import logging
import argparse

import django.apps
import django.conf
import django.contrib.auth.models
import django.core.management
import django.db.models
import django.db.transaction

import ezidapp.models.async_queue
import ezidapp.models.identifier
import impl.enqueue
import impl.nog_sql.counter
import impl.nog_sql.util

log = logging.getLogger(__name__)


class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.opt = None

    def create_parser(self, *args, **kwargs):
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = argparse.RawTextHelpFormatter
        return parser

    def add_arguments(self, parser):
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Debug level logging',
        )

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog_sql.util.log_setup(__name__, opt.debug)

        db = ORMStats()
        db.print_all()
        # db.print_identifier('ark:/13030/c80c4tkc')
        # db.print_identifier('ark:/13030/c8028pmk')


class ORMStats:
    def __init__(self):
        self.exit_stack = contextlib.ExitStack()
        self.counter = self.exit_stack.enter_context(impl.nog_sql.counter.Counter())
        self.page_size = django.conf.settings.QUERY_PAGE_SIZE

    def print_identifier(self, identifier):
        id_model = ezidapp.models.identifier.Identifier.objects.filter(identifier=identifier).get()
        # print(id_model)
        # pprint.pp(id_model.cm)

        # impl.nog.util.print_table(row_list, log.info)

    def print_all(self):
        # row_list = []
        row_list = [('MODEL', 'TABLE', 'ROWS')]
        for m in django.apps.apps.get_models(include_auto_created=True, include_swapped=True):
            row_list.append(
                (
                    m._meta.label,
                    m._meta.db_table,
                    m.objects.count(),
                    # ','.join(s.name for s in m._meta.fields),
                )
            )
        impl.nog_sql.util.print_table(row_list, log.info)
