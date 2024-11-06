#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Expunge expired test identifiers

Test identifiers older than Identifiers are discovered by querying the database directly, but expunged by
requesting that the (live) EZID server delete them.
"""

import logging
import time
from datetime import datetime
import urllib.error
from dateutil.parser import parse
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

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--pagesize', help='Rows in each batch select.', type=int)

        parser.add_argument(
            '--created_range_from', type=str,
            help = (
                'Created date range from - local date/time in ISO 8601 format without timezone \n'
                'YYYYMMDD, YYYYMMDDTHHMMSS, YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS. \n'
                'Examples: 20241001, 20241001T131001, 2024-10-01, 2024-10-01T13:10:01 or 2024-10-01'
            )
        )
        
        parser.add_argument(
            '--created_range_to', type=str,
            help = (
                'Created date range to - local date/time in ISO 8601 format without timezone \n'
                'YYYYMMDD, YYYYMMDDTHHMMSS, YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS. \n'
                'Examples: 20241001, 20241001T131001, 2024-10-01, 2024-10-01T13:10:01 or 2024-10-01'
            )
        )
    
    def run(self):
        
        BATCH_SIZE = self.opt.pagesize
        if BATCH_SIZE is None:
            BATCH_SIZE = 1000
        
        created_from = None
        created_to = None
        created_from_str = self.opt.created_range_from
        created_to_str = self.opt.created_range_to
        if created_from_str is not None:
            try:
                created_from = self.date_to_seconds(created_from_str)
            except Exception as ex:
                log.error(f"Input date/time error: {ex}")
                exit()
        if created_to_str is not None:
            try:
                created_to = self.date_to_seconds(created_to_str)
            except Exception as ex:
                log.error(f"Input date/time error: {ex}")
                exit()
        
        if created_from is not None and created_to is not None:
            time_range = Q(createTime__gte=created_from) & Q(createTime__lte=created_to)
            time_range_str = f"updated between: {created_from_str} and {created_to_str}"
        elif created_to is not None:
            time_range = Q(createTime__lte=created_to)
            time_range_str = f"updated before: {created_to_str}"
        else:
            max_age_ts = int(time.time()) - django.conf.settings.DAEMONS_EXPUNGE_MAX_AGE_SEC
            min_age_ts = max_age_ts - django.conf.settings.DAEMONS_EXPUNGE_MAX_AGE_SEC
            time_range = Q(createTime__gte=min_age_ts) & Q(createTime__lte=max_age_ts)
            time_range_str = f"updated between: {self.seconds_to_date(min_age_ts)} and {self.seconds_to_date(max_age_ts)}"
        
        min_id, max_id = self.get_id_range_by_time(time_range)
        filter_by_id = None

        log.info(f"Initial time range: {time_range}")
        log.info(f"Initial min & max IDs: {min_id} : {max_id}")

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
            else:
                combined_filter &= time_range

            qs = (
                ezidapp.models.identifier.Identifier.objects.filter(combined_filter)
                    .only("identifier").order_by("pk")[: BATCH_SIZE]
            )

            log.info(f"filter: {combined_filter}")
            log.info(f"Query returned {len(qs)} records.")
            for si in qs:
                min_id = si.id
                with django.db.transaction.atomic():
                    impl.enqueue.enqueue(si, "delete", updateExternalServices=True)
                    si.delete()

            if len(qs) < BATCH_SIZE:
                if created_from is not None or created_to is not None:
                    log.info(f"Finished time range: {time_range_str}")
                    exit()
                else:
                    sleep_time = django.conf.settings.DAEMONS_LONG_SLEEP
                    log.info(f"Sleep {sleep_time} sec before running next batch.")
                    self.sleep(sleep_time)
                    min_age_ts = max_age_ts
                    max_age_ts = int(time.time()) - django.conf.settings.DAEMONS_EXPUNGE_MAX_AGE_SEC
                    time_range = Q(createTime__gte=min_age_ts) & Q(createTime__lte=max_age_ts)
                    min_id, max_id = self.get_id_range_by_time(time_range)
            else:
                self.sleep(django.conf.settings.DAEMONS_BATCH_SLEEP)

    def get_id_range_by_time(self, time_range: Q):
        first_id = last_id = None
        
        if time_range is not None:
            queryset = (
                ezidapp.models.identifier.Identifier.objects
                .filter(time_range).only("id").order_by("pk")
            )
            
            first_record = queryset.first()
            last_record = queryset.last()
            
            if first_record is not None:
                first_id = first_record.id

            if last_record is not None:
                last_id = last_record.id
        
        return first_id, last_id
    
    
    def date_to_seconds(self, date_time_str: str) -> int:
        """
        Convert date/time string to seconds since the Epotch.
        For example:
        2024-01-01 00:00:00 => 1704096000
        2024-10-10 00:00:00 => 1728543600

        Parameter:
        date_time_str: A date/time string in in ISO 8601 format without timezone.
        For example: 'YYYYMMDD, YYYYMMDDTHHMMSS, YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS.

        Returns:
        int: seconds since the Epotch

        """

        # Parse the date and time string to a datetime object
        dt_object = parse(date_time_str)

        # Convert the datetime object to seconds since the Epoch
        seconds_since_epoch = int(dt_object.timestamp())

        return seconds_since_epoch

   
    def seconds_to_date(self, seconds_since_epoch: int) -> str:
        dt_object = datetime.fromtimestamp(seconds_since_epoch)

        # Format the datetime object to a string in the desired format
        formatted_time = dt_object.strftime("%Y-%m-%dT%H:%M:%S")
        return formatted_time


