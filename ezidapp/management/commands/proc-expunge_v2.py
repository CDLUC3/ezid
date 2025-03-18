#! /usr/bin/env python

#  Copyright©2024, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Expunge expired test identifiers

Test identifiers older than two weeks are discovered by querying the database directly, but expunged by
requesting that the (live) EZID server delete them.
"""

import logging
import argparse
import time
from datetime import datetime, date, timedelta
from dateutil.parser import parse

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
import impl.nog_sql.util


log = logging.getLogger(__name__)


class Command(django.core.management.BaseCommand):
    help = __doc__
    name = __name__


    def __init__(self):
        super(Command, self).__init__()

    def add_arguments(self, parser):
        parser.add_argument(
            '--batchsize', help='Rows in each batch select.', type=int)

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

        parser.add_argument(
            '--debug',
            action='store_true',
            help='Debug level logging',
        )
    
    def handle(self, *_, **opt):
        options = argparse.Namespace(**opt)
        impl.nog_sql.util.log_setup(__name__, options.debug)

        BATCH_SIZE = options.batchsize
        if BATCH_SIZE is None:
            BATCH_SIZE = 1000
                
        created_from_ts = None
        created_to_ts = None
        created_from_str = options.created_range_from
        created_to_str = options.created_range_to
        if created_from_str is not None:
            try:
                created_from_ts = self.date_to_seconds(created_from_str)
            except Exception as ex:
                log.error(f"Input date/time error: {ex}")
                exit()
        if created_to_str is not None:
            try:
                created_to_ts = self.date_to_seconds(created_to_str)
            except Exception as ex:
                log.error(f"Input date/time error: {ex}")
                exit()
        
        self.start_time = datetime.now()

        log.info(f"expunge started: {self.start_time}")
        log.info(f"created_range_from: {created_from_str}")
        log.info(f"created_range_to: {created_to_str}")
        
        if created_from_ts is not None and created_to_ts is not None:
            if created_from_ts >= created_to_ts:
                log.error(f"The date/time of created_range_from {created_from_str} should be earlier than created_range_to {created_to_str}.")
                exit()
            time_range_str = f"between: {created_from_str} and {created_to_str}"
            time_range = Q(createTime__gte=created_from_ts) & Q(createTime__lte=created_to_ts)
            log.info(f"Use command options for date/time range.")
        elif created_from_ts is None and created_to_ts is None:
            log.info(f"Setup default time range.")
            expunge_max_age_days = django.conf.settings.DAEMONS_EXPUNGE_MAX_AGE_SEC / (60 * 60 * 24)
            expunge_date = date.today() - timedelta(days=expunge_max_age_days + 1)
            created_from_ts = int(datetime.combine(expunge_date, datetime.min.time()).timestamp())
            created_to_ts = int(datetime.combine(expunge_date, datetime.max.time()).timestamp())
            time_range_str = f"between: {self.seconds_to_date(created_from_ts)} and {self.seconds_to_date(created_to_ts)}"
            time_range = Q(createTime__gte=created_from_ts) & Q(createTime__lte=created_to_ts)      
        else:
            log.error(f"The created_range_from and created_range_to options should be provied in pairs.")
            exit()

        min_id, max_id = self.get_id_range_by_time(time_range)

        log.info(f"Initial time range: {time_range_str}, {time_range}")
        log.info(f"Initial ID range: {min_id} : {max_id}")
        log.info(f"Batch size: {BATCH_SIZE}")

        while True:
            # TODO: This is a heavy query which can be optimized with better indexes or
            # flags in the DB.
            filter_by_id = None
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
            if filter_by_id is None:
                self.exit_proc(f"No records returned for time range: {time_range_str}, {time_range}")

            combined_filter &= filter_by_id
            log.info(f"Combined filter: {combined_filter}")
        
            try:
                qs = (
                    ezidapp.models.identifier.Identifier.objects.filter(combined_filter)
                        .order_by("id")[: BATCH_SIZE]
                )

                log.info(f"Query with BATCH_SIZE {BATCH_SIZE} returned {len(qs)} records.")
                for si in qs:
                    min_id = si.id
                    with django.db.transaction.atomic():
                        log.info(f"Delete testing identifier: {si.identifier}")
                        impl.enqueue.enqueue(si, "delete", updateExternalServices=True)
                        si.delete()

                if len(qs) < BATCH_SIZE:
                    self.exit_proc(f"Finished time range: {time_range_str}, {time_range}")
                else:
                    log.info("Continue processing next batch ...")
                    time.sleep(django.conf.settings.DAEMONS_BATCH_SLEEP)

            except Exception as ex:
                self.exit_proc(f"Database error: {ex}", error=1)


    def get_id_range_by_time(self, time_range: Q):
        first_id = last_id = None
        
        if time_range is not None:
            try:
                queryset = (
                    ezidapp.models.identifier.Identifier.objects
                    .filter(time_range).only("id").order_by("id")
                )
                
                first_record = queryset.first()
                last_record = queryset.last()
                
                if first_record is not None:
                    first_id = first_record.id

                if last_record is not None:
                    last_id = last_record.id
            except Exception as ex:
                log.error(f"Database error while retrieving records from Identifier for time range: {time_range} : {ex}")
        
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
    
    def exit_proc(self, message: str, error=None):
        end_time = datetime.now()
        if error is not None:
            log.error(message)
        else:
            log.info(message)
        log.info(f"expunge ended: {end_time}")
        log.info(f"execution time: {end_time - self.start_time}")
        exit()
    


