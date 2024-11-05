#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Expunge expired test identifiers

Test identifiers older than Identifiers are discovered by querying the database directly, but expunged by
requesting that the (live) EZID server delete them.
"""

import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.response

import django.conf
import django.conf
import django.db
import django.db.transaction

import ezidapp.management.commands.proc_base
import ezidapp.models.identifier
import ezidapp.models.identifier
import ezidapp.models.news_feed
import ezidapp.models.shoulder
from django.db.models import Q

import impl.enqueue
import impl.ezid

log = logging.getLogger(__name__)


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    name = __name__
    setting = 'DAEMONS_EXPUNGE_ENABLED'

    def __init__(self):
        super().__init__()

    def run(self):
        BATCH_SIZE = 10
        max_age_ts = int(time.time()) - django.conf.settings.DAEMONS_EXPUNGE_MAX_AGE_SEC
        min_age_ts = max_age_ts - 2* django.conf.settings.DAEMONS_EXPUNGE_MAX_AGE_SEC

        min_id, max_id = self.get_id_range_by_time(min_age_ts, max_age_ts)
        filter_by_id = None

        while not self.terminated():
            # TODO: This is a heavy query which can be optimized with better indexes or
            # flags in the DB.
            if min_id is not None:
                filter_by_id = Q(id__gte=min_id)
            if max_id is not None:
                if filter_by_id is not None:
                    filter_by_id &= Q(id__lte=max_id)
                else:
                    filter_by_id = Q(id__lte=max_id)
            
            combined_filter = (
                    Q(identifier__startswith=django.conf.settings.SHOULDERS_ARK_TEST)
                    | Q(identifier__startswith=django.conf.settings.SHOULDERS_DOI_TEST)
                    | Q(identifier__startswith=django.conf.settings.SHOULDERS_CROSSREF_TEST)
                )
            if filter_by_id is not None:
                combined_filter &= filter_by_id

            print(min_age_ts)
            print(max_age_ts)
            print(min_id)
            print(max_id)
            print(combined_filter)

            qs = (
                ezidapp.models.identifier.Identifier.objects.filter(combined_filter)
                    .only("identifier").order_by("pk")[: BATCH_SIZE]
            )

            if not qs:
                self.sleep(django.conf.settings.DAEMONS_LONG_SLEEP)
                min_age_ts = max_age_ts
                max_age_ts = int(time.time()) - django.conf.settings.DAEMONS_EXPUNGE_MAX_AGE_SEC
                min_id, max_id = self.get_id_range_by_time(min_age_ts, max_age_ts)
                continue

            for si in qs:
                min_id = si.id
                with django.db.transaction.atomic():
                    impl.enqueue.enqueue(si, "delete", updateExternalServices=True)
                    si.delete()

            self.sleep(django.conf.settings.DAEMONS_BATCH_SLEEP)

    def get_id_range_by_time(self, min_age_ts, max_age_ts):
        first_id = last_id = None
        filter_by_time = None
        if min_age_ts is not None:
            filter_by_time = Q(createTime__gte=min_age_ts)
        if max_age_ts is not None:
            if filter_by_time is not None:
                filter_by_time &= Q(createTime__lte=max_age_ts)
            else:
                filter_by_time = Q(createTime__lte=max_age_ts)
        
        print(filter_by_time)
        if filter_by_time is not None:
            queryset = (
                ezidapp.models.identifier.Identifier.objects
                .filter(filter_by_time).only("id").order_by("pk")
            )
            
            first_record = queryset.first()
            last_record = queryset.last()
            
            if first_record is not None:
                first_id = first_record.id

            if last_record is not None:
                last_id = last_record.id
        
        return first_id, last_id


