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

import django.conf
import django.conf
import django.db
import django.db.transaction

import ezidapp.management.commands.proc_base
import ezidapp.models.identifier
import ezidapp.models.shoulder
from django.db.models import Q

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


    def run(self):
        """
            Checks for the successfully processed identifier

            Args:
                None
        """
        # keep running until terminated
        while not self.terminated():
            currentTime=int(time.time())
            timeDelta=django.conf.settings.DAEMONS_CHECK_IDENTIFIER_ASYNC_STATUS_TIMESTAMP

            # retrieve identifiers with update timestamp within a set range
            refIdsQS = self.refIdentifier.objects.filter(
                updateTime__lte=currentTime,
                updateTime__gte=currentTime - timeDelta
            ).order_by("-pk")[: django.conf.settings.DAEMONS_MAX_BATCH_SIZE]

            log.info("Checking ref Ids in the range: " + str(currentTime) + " - " + str(currentTime - timeDelta))

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
                queue.objects.filter(id=primary_key).delete()
            else:
                log.info("Delete async entry: " + str(primary_key))
                queue.objects.filter(seq=primary_key).delete()
        except Exception as e:
            log.error("Exception occured while processing identifier '" + identifier + "' for '" +
                        record_type + "' table")
            log.error(e)
