#! /usr/bin/env python

#  Copyright©2024, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""

Delete async queue entries identified by the refIdentifiers listed in the input file.

"""

import logging
import time
import csv
from typing import List

import django.conf
import django.conf
import django.db
import django.db.transaction

import ezidapp.management.commands.proc_base
import ezidapp.models.identifier
import ezidapp.models.shoulder
from django.db.models import Q
import impl
import impl.nog_sql.util

log = logging.getLogger(__name__)

class Command(django.core.management.BaseCommand):
    help = __doc__
    name = __name__

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
        parser.add_argument('-i', '--id_file', type=str, help='Identifier file', required=True)
        parser.add_argument('--debug', action='store_true', help='Debug level logging')

    
    def handle(self, *args, **opt):
        impl.nog_sql.util.log_setup(__name__, opt.get('debug'))

        log.info(f"Update identifier status in the async queues so they can be cleaned up by the proc-cleanup-async-queues job.")

        identifier_file = opt.get('id_file')
        identifier_list = self.loadIdFile(identifier_file)

        log.info(f"Identifiers are provided by input file {identifier_file}")

        for identifier in identifier_list:
            try:
                queue_entry = self.refIdentifier.objects.get(identifier=identifier)
                refId = queue_entry.id
                log.info(f"Update refIdentifier status: refID={refId}, identifier={identifier}")
                
                updated = False
                # check if the identifier is in each queue 
                for key, value in self.queueType.items():
                    queue_name = key
                    queue_model = value

                    qs = queue_model.objects.filter(Q(refIdentifier_id=refId))

                    if not qs:
                        log.info(f"refID={refId}, identifier={identifier} is not in {queue_name} queue, skip")
                        continue

                    for queue_entry in qs:
                        log.info(f"Update identifier: {refId} in {queue_name} queue")
                        self.update_status(queue_model, queue_entry.pk, queue_model.IGNORED, refId=refId, identifier=identifier)
                        updated = True

                if updated:
                    current_time=int(time.time())
                    try:
                        self.refIdentifier.objects.filter(id=refId).update(updateTime=current_time)
                    except Exception as e:
                        log.error(f"error:{e}")

            except self.refIdentifier.DoesNotExist:
                log.error(f"Identifier {identifier} does not exist in RefIdentifier table.")
            except Exception as ex:
                log.error(f"Retrieve identifier {identifier} had error: {ex}")


    def update_status(self, queue, primary_key, status, refId=None, identifier=None):
        try:
            queue.objects.filter(seq=primary_key).update(status=status)
            log.info(f"Updated {queue.__name__} entry status to {status}: seq={primary_key}, refID={refId}, identifier={identifier}")
        except Exception as e:
            log.error(f"Exception occured while updating {queue.__name__} entry status to {status}: seq={primary_key}, refID={refId}, identifier={identifier}")
            log.error(f"Error: {e}")

    
    def loadIdFile(self, filename: str)->  List[str]:
        """
            Read identifiers from a CSV file.
            The identifiers are listed in the 'identifer' column.
        Args:
            filename (str): input filename

        Returns:
            List of identifiers from the input file
        """
        if filename is None:
            return None
        
        id_list = []
        with open(filename) as file:
            csvreader = csv.DictReader(file, delimiter='\t')
            for line in csvreader:
                identifier =  line.get('identifier')
                if identifier:
                    id_list.append(identifier)
  
        return id_list
