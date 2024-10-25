#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""

Clean up entries that are successfully completed or are a 'no-op'

Identifier operation entries are retrieved by querying the database;
operations that successfully completed or are a no-op are deleted based on
pre-set interval.

"""

import logging
import time
from datetime import datetime
from dateutil.parser import parse

import django.conf
import django.db
from django.db import transaction
from django.db.models import Q

import ezidapp.management.commands.proc_base
import ezidapp.models.identifier
import ezidapp.models.shoulder


log = logging.getLogger(__name__)


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    name = __name__

    setting = 'DAEMONS_QUEUE_CLEANUP_ENABLED'

    queueType = {
        'crossref': ezidapp.models.async_queue.CrossrefQueue,
        'datacite': ezidapp.models.async_queue.DataciteQueue,
        'search': ezidapp.models.async_queue.SearchIndexerQueue
    }

    refIdentifier = ezidapp.models.identifier.RefIdentifier

    def __init__(self):
        super().__init__()

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--pagesize', help='Rows in each batch select.', type=int)

        parser.add_argument(
            '--updated_range_from', type=str,
            help = (
                'Updated date range from - local date/time in ISO 8601 format without timezone \n'
                'YYYYMMDD, YYYYMMDDTHHMMSS, YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS. \n'
                'Examples: 20241001, 20241001T131001, 2024-10-01, 2024-10-01T13:10:01 or 2024-10-01'
            )
        )
        
        parser.add_argument(
            '--updated_range_to', type=str,
            help = (
                'Updated date range to - local date/time in ISO 8601 format without timezone \n'
                'YYYYMMDD, YYYYMMDDTHHMMSS, YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS. \n'
                'Examples: 20241001, 20241001T131001, 2024-10-01, 2024-10-01T13:10:01 or 2024-10-01'
            )
        )
        

    def run(self):
        """
            Checks for the successfully processed identifier

            Args:
                None
        """
        ASYNC_CLEANUP_SLEEP = 60

        BATCH_SIZE = self.opt.pagesize
        if BATCH_SIZE is None:
            BATCH_SIZE = 10000
        
        updated_from = None
        updated_to = None
        updated_from_str = self.opt.updated_range_from
        updated_to_str = self.opt.updated_range_to
        if updated_from_str is not None:
            try:
                updated_from = self.date_to_seconds(updated_from_str)
            except Exception as ex:
                log.error(f"Input date/time error: {ex}")
                exit()
        if updated_to_str is not None:
            try:
                updated_to = self.date_to_seconds(updated_to_str)
            except Exception as ex:
                log.error(f"Input date/time error: {ex}")
                exit()
        
        if updated_from is not None and updated_to is not None:
            time_range = Q(updateTime__gte=updated_from) & Q(updateTime__lte=updated_to)
            time_range_str = f"updated between: {updated_from_str} and {updated_to_str}"
        elif updated_to is not None:
            time_range = Q(updateTime__lte=updated_to)
            time_range_str = f"updated before: {updated_to_str}"
        else:
            max_age_ts = int(time.time()) - django.conf.settings.DAEMONS_EXPUNGE_MAX_AGE_SEC
            min_age_ts = max_age_ts - django.conf.settings.DAEMONS_EXPUNGE_MAX_AGE_SEC
            time_range = Q(updateTime__gte=min_age_ts) & Q(updateTime__lte=max_age_ts)
            time_range_str = f"updated between: {self.seconds_to_date(min_age_ts)} and {self.seconds_to_date(max_age_ts)}"

        last_id = 0
        # keep running until terminated
        while not self.terminated():
            # retrieve identifiers with update timestamp within a date range
            filter = time_range & Q(id__gt=last_id)
            refIdsQS = self.refIdentifier.objects.filter(filter).order_by("pk")[: BATCH_SIZE]

            log.info(f"Checking ref Ids: {time_range_str}")
            log.info(f"Checking ref Ids returned: {len(refIdsQS)} records")

            # iterate over query set to check each identifier status
            for refId in refIdsQS:

                # set status for each handle system
                identifierStatus = {
                    'crossref' : False,
                    'datacite' : False,
                    'search' : False
                }

                # check if the identifier is processed for each background job 
                for key, value in self.queueType.items():
                    queue = value

                    qs = queue.objects.filter(
                        Q(refIdentifier_id=refId.pk)
                    )

                    # if the identifier does not exist in the table
                    # mark as 'OK' to delete from the refIdentifier
                    if not qs:
                        identifierStatus[key] = True
                        continue

                    for task_model in qs:
                        log.info('-' * 10)
                        log.info("Running job for identifier: " + refId.identifier + " in " + key + " queue")

                        # delete identifier if the status is successfully synced or
                        # not applicable for this handle system
                        if (task_model.status==queue.SUCCESS or task_model.status==queue.IGNORED):
                            log.info(
                                "Delete identifier: " + refId.identifier + " in " + key + " queue")
                            identifierStatus[key] = True
                            self.deleteRecord(queue, task_model.pk, record_type=key, identifier=refId.identifier)

                # if the identifier is successfully processed for all the handle system
                # delete it from the refIdentifier table
                if all(i for i in identifierStatus.values()):
                    log.info(
                        "Delete identifier: " + refId.identifier + " from refIdentifier table.")
                    self.deleteRecord(self.refIdentifier, refId.pk, record_type='refId', identifier=refId.identifier)

            last_id = refId.pk
            if len(refIdsQS) < BATCH_SIZE:
                if updated_from is not None or updated_to is not None:
                    log.info(f"Finished - Checking ref Ids: {time_range_str}")
                    exit()
                else:
                    log.info(f"Sleep {ASYNC_CLEANUP_SLEEP} seconds before processing next batch")
                    self.sleep(ASYNC_CLEANUP_SLEEP)
                    max_age_ts = min_age_ts
                    min_age_ts = max_age_ts - ASYNC_CLEANUP_SLEEP
                    time_range = Q(updateTime__gte=min_age_ts) & Q(updateTime__lte=max_age_ts)
                    time_range_str = f"updated between: {self.seconds_to_date(min_age_ts)} and {self.seconds_to_date(max_age_ts)}"
            else:
                self.sleep(django.conf.settings.DAEMONS_BATCH_SLEEP)

    def deleteRecord(self, queue, primary_key, record_type=None, identifier=None):
        """
            Deletes the identifier record that has been successfully completed
            based on the record's primary key provided

        Args:
            queue : async handle queue
            primary_key (str): primary key of the record to be deleted.
            record_type (str): . Defaults to None.
            identifier (str): . Defaults to None.
        """
        try:
            # check if the record to be deleted is a refIdentifier record
            if (record_type is not None and record_type == 'refId'):
                log.info(type(queue))
                log.info("Delete refId: " + str(primary_key))
                with transaction.atomic():
                    obj = queue.objects.select_for_update().get(id=primary_key)
                    obj.delete()
            else:
                log.info(f"Delete async queue {queue.__name__} entry: " + str(primary_key))
                with transaction.atomic():
                    obj = queue.objects.select_for_update().get(seq=primary_key)
                    obj.delete()
        except Exception as e:
            log.error("Exception occured while processing identifier '" + identifier + "' for '" +
                        record_type + "' table")
            log.error(e)


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