"""Check that metadata stored in compressed blobs is valid.

The following fields contain compressed blobs:

ezidapp_binderqueue       metadata
ezidapp_crossrefqueue     metadata
ezidapp_datacitequeue     metadata
ezidapp_searchidentifier  cm
ezidapp_storeidentifier   cm
ezidapp_updatequeue       object
"""
import json
import logging
import zlib

import django.conf
import django.contrib.auth.models
import django.core.management
import django.db.transaction
import pymysql.cursors

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
        # Connect to the database
        connection = pymysql.connect(
            host=django.conf.settings.DATABASES['default']['HOST'],
            user=django.conf.settings.DATABASES['default']['USER'],
            password=django.conf.settings.DATABASES['default']['PASSWORD'],
            database=django.conf.settings.DATABASES['default']['NAME'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
        )

        with connection.cursor(pymysql.cursors.SSDictCursor) as cursor:
            sql = "select cm from ezid.ezidapp_storeidentifier"
            cursor.execute(
                sql,
                tuple(),
            )

            while True:
                blob_list = cursor.fetchmany(10000)
                for d in blob_list:
                    blob_bytes = zlib.decompress(d['cm'])
                    j = json.loads(blob_bytes)
                x += len(blob_list)
