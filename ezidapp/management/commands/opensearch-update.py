from django.core.management.base import BaseCommand
from django.conf import settings
from ezidapp.models.identifier import Identifier
from impl.open_search_doc import OpenSearchDoc
import json
import pdb
import requests
import datetime
import impl.open_search_schema as oss

# this is only for the time being since I'm using a local server without correct SSL/https
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Disable only the InsecureRequestWarning
urllib3.disable_warnings(InsecureRequestWarning)
# end suppression of urllib3 InsecureRequestWarning

SPLIT_SIZE = 100

# run: python manage.py opensearch-update


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Get all items from Identifier table 100 at a time manually since
        # I had lockup issues with the ORM, even with constructs that were
        # supposed to be lazy and handle large datasets. :shrug:
        #
        # all_identifiers = Identifier.objects.all().iterator(chunk_size=20)
        # for ident in all_identifiers: ...
        # ^^^ The above code would lock up ^^^

        # create the index if it doesn't exist from the schema
        if oss.index_exists() is False:
            print('index does not exists, so creating it')
            oss.create_index()

        string_parts = []
        counter = 0
        if options['starting_primary_id']:
            start_after_id = options['starting_primary_id']
        else:
            start_after_id = 0

        while True:
            iden_arr = Identifier.objects.filter(id__gt=start_after_id).order_by('id')[:100]
            # break when we run out of items
            if not iden_arr:
                break

            for identifier in iden_arr:
                string_parts.append(self._bulk_update_pair(identifier))
                start_after_id = identifier.id

                if (counter + 1) % SPLIT_SIZE == 0:
                    # time to send to OpenSearch
                    result = self._do_bulk_update(string_parts)

                    # handle the result and do something if error? log or what?
                    if result is False:
                        print("Error in bulk update")
                        pdb.set_trace()
                    else:
                        print(f'Total {counter+1} items updated in OpenSearch (at primary ID: {identifier.id}).')
                    # reset the accumulator
                    string_parts = []

                counter += 1

    def add_arguments(self, parser):
        parser.add_argument('starting_primary_id', type=int, nargs='?', default=0,
                            help='Starting primary ID from database (default 0)')

    # see https://opensearch.org/docs/latest/api-reference/document-apis/bulk/
    @staticmethod
    def _bulk_update_pair(identifier: Identifier) -> str:
        my_os = OpenSearchDoc(identifier=identifier)
        my_dict = my_os.dict_for_identifier()
        my_dict['open_search_updated'] = datetime.datetime.now().isoformat()
        line1 = json.dumps({"index": {"_index": settings.OPENSEARCH_INDEX, "_id": identifier.identifier}})
        line2 = json.dumps(my_dict)
        return f"{line1}\n{line2}"

    @staticmethod
    def _do_bulk_update(string_parts: list) -> bool:
        # The URL for the OpenSearch endpoint
        url = f'{settings.OPENSEARCH_BASE}/_bulk'
        # Convert the dictionary into a JSON string
        json_string = "\n".join(string_parts) + "\n"  # must have a trailing newline
        # Send POST request
        response = requests.post(url,
                                 data=json_string,
                                 headers={'Content-Type': 'application/json'},
                                 auth=(settings.OPENSEARCH_USER, settings.OPENSEARCH_PASSWORD),
                                 verify=False)

        # the response may have "errors": true if there are issues and has an items array with the errors
        # the array has a dict with "status" (success in the 200s) and "error" (the error dict)

        # Check the response
        if response.status_code == 200:
            return True
        else:
            return False




