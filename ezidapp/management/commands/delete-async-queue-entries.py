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

    
    def handle(self, *args, **opt):
        identifier_file = opt.get('id_file')
        print(identifier_file)
        identifier_list = self.loadIdFile(identifier_file)
        print(identifier_list)

        for identifier in identifier_list:
            try:
                record = self.refIdentifier.objects.get(identifier=identifier)
                refId = record.id
                print(f"{refId}, {identifier}")
                
                updated = None
                # check if the identifier is processed for each background job 
                for key, value in self.queueType.items():
                    queue = value

                    qs = queue.objects.filter(
                        Q(refIdentifier_id=refId)
                    )

                    if not qs:
                        continue

                    for task_model in qs:
                        log.info('-' * 10)
                        log.info(f"Update identifier: {refId} in {key} {queue}")
                        self.update_status(queue, task_model.pk, record_type=key, identifier=refId, status=queue.IGNORED)
                        updated = True

                if updated is not None:
                    current_time=int(time.time())
                    try:
                        self.refIdentifier.objects.filter(id=refId).update(updateTime=current_time)
                    except Exception as e:
                        print(f"error:{e}")

            except Exception as ex:
                print(f"Retrieve identifier  {identifier} had error: error: {ex}")
        exit()


    def update_status(self, queue, primary_key, record_type=None, identifier=None, status=None):
        try:
            log.info("Update async entry: " + str(primary_key))
            queue.objects.filter(seq=primary_key).update(status=status)
        except Exception as e:
            log.error("Exception occured while processing identifier '" + identifier + "' for '" +
                        record_type + "' table")
            log.error(e)

    
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
