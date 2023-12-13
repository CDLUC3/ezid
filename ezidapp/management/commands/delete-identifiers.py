import csv
import logging
from django.core.management.base import BaseCommand
from django.db.models import Q
import django.conf
import django.db
import django.db.transaction
from ezidapp.models.identifier import Identifier
from ezidapp.management.commands.proc_base import AsyncProcessingCommand
import impl.enqueue

log = logging.getLogger(__name__)

class Command(AsyncProcessingCommand):
    help = "Expunge identifiers listed in a CSV file"

    def __init__(self):
        super().__init__()

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file containing identifiers in the first column.')
        parser.add_argument('--update-external-services', action='store_true', dest='update_external_services',
                            help='Update external services after expunging identifiers.')

    def run(self, *args, **kwargs):
        csv_file_path = kwargs['csv_file']
        update_external_services = kwargs['update_external_services']

        with open(csv_file_path, 'r') as csv_file:
            identifier_reader = csv.reader(csv_file)
            identifiers = [row[0] for row in identifier_reader]

        qs = Identifier.objects.filter(identifier__in=identifiers).only("identifier")

        if not qs:
            log.info("No identifiers found for deletion.")
            return

        for si in qs:
            with django.db.transaction.atomic():
                impl.enqueue.enqueue(si, "delete", updateExternalServices=update_external_services)
                si.delete()

        log.info("Identifiers successfully expunged. Script completed")
