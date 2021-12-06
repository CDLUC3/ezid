"""Check that metadata stored in compressed blobs is valid

This performs basic integrity checks and calculates some statistics on the values of all compressed blobs stored in the database.

Integrity checks include:

    - Check that the object can be successfully deserialized (uncompressed and parsed into a Python object)
    - Check that the object deserializes into the expected type

Statistics include:

    - Number of unique objects

EZID stores compressed blobs in the following locations:

    Model             Field       Table

    BinderQueue       metadata    ezidapp_binderqueue
    CrossrefQueue     metadata    ezidapp_crossrefqueue
    DataciteQueue     metadata    ezidapp_datacitequeue
    Identifier  cm          ezidapp_searchidentifier
    Identifier   cm          ezidapp_storeidentifier

There are three basic types of blobs:

metadata: Compressed JSON that deserializes into a Python dict
cm:       Compressed Python code that serializes into a Python dict
object:   Compressed JSON that deserializes into a Identifier Model

"""
#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import contextlib
import json
import logging

import django.apps
import django.conf
import django.contrib.auth.models
import django.core.management
import django.db.models
import django.db.transaction

import pymysql.cursors

import impl.nog.counter
import impl.nog.tb

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
        db = ViaORM()
        db.list_blobs_all()


class ViaORM:
    def __init__(self):
        self.exit_stack = contextlib.ExitStack()
        self.counter = self.exit_stack.enter_context(impl.nog.counter.Counter())
        self.page_size = django.conf.settings.QUERY_PAGE_SIZE

    def list_blobs_all(self):
        for model_name, field_name, is_queue in django.conf.settings.BLOB_FIELD_LIST:
            print(model_name, field_name, is_queue)
            log.info(f'{model_name}:')
            model = django.apps.apps.get_model('ezidapp', model_name)
            self.list_blobs_field(model, model_name, field_name)

    def list_blobs_field(self, model, model_name, field_name):
        max_row = model.objects.aggregate(django.db.models.Count('pk'))['pk__count']

        for i in range(0, max_row + self.page_size + 1, self.page_size):
            for r in (
                model.objects.filter(pk__gte=i, pk__lt=i + self.page_size)
                .all()
                .values(field_name)
            ):
                pass

                # blob_bytes = zlib.decompress(d['cm'])
                # j = json.loads(blob_bytes)
                # log.info(blob_bytes)
                # v = getattr(r, field_name)

                # v = r[field_name]
                # print(v)

                # self.counter.count('', f'total')
                # self.counter.count('', f'{model_name}')
                # self.counter.count('', f'{model_name}.{field_name}')

                # blob_str = f'{model_name}.{field_name} type {r!r}'
                # print(blob_str)
                # field_obj = getattr(r, field_name)


# class DirectToDatabase:
#     """Methods that interact directly with the DB, providing a view that is unfiltered by the ORM."""
#
#     def __init__(self):
#         self.connection = self.connect()
#
#     def decode_object_field(self, **opt):
#         with self.connection.cursor(pymysql.cursors.SSDictCursor) as cursor:
#             sql = "select object from ezidapp_updatequeue"
#             cursor.execute(sql, tuple())
#
#             checked_total = 0
#             while True:
#                 blob_list = cursor.fetchmany(1000)
#                 for d in blob_list:
#                     blob_bytes = zlib.decompress(d['object'])
#                     j = json.loads(blob_bytes)
#                     log.info(blob_bytes)
#                 checked_total += len(blob_list)
#                 if checked_total >= 10000 or not len(blob_list):
#                     log.info('stopping...')
#                     return
#
#     def decode_storeidentifier_cm(self):
#         self.connection = self.connect()
#
#         with self.connection.cursor(pymysql.cursors.SSDictCursor) as cursor:
#             sql = "select cm from ezid.ezidapp_storeidentifier where identifier='ark:/86073/b3d07s'"
#             cursor.execute(sql, tuple())
#
#             checked_total = 0
#             while True:
#                 blob_list = cursor.fetchmany(1000)
#                 for d in blob_list:
#                     blob_bytes = zlib.decompress(d['cm'])
#                     j = json.loads(blob_bytes)
#                     log.info(blob_bytes)
#                 checked_total += len(blob_list)
#                 if checked_total >= 10000 or not len(blob_list):
#                     log.info('stopping...')
#                     return
#
#     def connect(self):
#         # Connect to the database
#         connection = pymysql.connect(
#             host=django.conf.settings.DATABASES['default']['HOST'],
#             user=django.conf.settings.DATABASES['default']['USER'],
#             password=django.conf.settings.DATABASES['default']['PASSWORD'],
#             database=django.conf.settings.DATABASES['default']['NAME'],
#             charset='utf8mb4',
#             cursorclass=pymysql.cursors.DictCursor,
#         )
#         return connection
