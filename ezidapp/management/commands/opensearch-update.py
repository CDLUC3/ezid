from django.core.management.base import BaseCommand
from django.conf import settings
from ezidapp.models.identifier import SearchIdentifier
from impl.open_search_doc import OpenSearchDoc
import json
import datetime
import impl.open_search_schema as oss
from django.db.models import Q
import dateutil.parser


# this is only for the time being since I'm using a local server without correct SSL/https
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Disable only the InsecureRequestWarning
urllib3.disable_warnings(InsecureRequestWarning)
# end suppression of urllib3 InsecureRequestWarning

SPLIT_SIZE = 10
DB_PAGE_SIZE = 100

# run: python manage.py opensearch-update
# optional parameters: --starting_id 1234 --updated_since 2023-10-10T00:00:00Z
# --starting_id is the primary key ID to start populating from (good for resuming after a crash while populating all)
# --updated_since is a date in ISO 8601 format (YYYY-MM-DDTHH:MM:SS) to filter by updated time
# it allows you to only populate items updated after a certain date/time, which should make the population much faster
# because no need to repopulate all items for the entire history.

# Even if items are already up-to-date, it doesn't hurt to repopulate them since it just updates from the
# copy of record which is the database values. OpenSearach values are derived for search and display purposes.

# NOTE: This script will need revision if the SearchIdentifier model is ever removed from EZID since it relies on the
# SearchIdentifier update time to determine what to update in OpenSearch.  It could be modified to use the
# Identifier update time instead, but that might be a different time that does not take into account the link checker
# which is updates in the SearchIdentifier table and doesn't update the Identifier table.


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Get all items from Identifier table DB_PAGE_SIZE at a time manually since
        # I had lockup issues with the ORM, even with constructs that were
        # supposed to be lazy and handle large datasets. :shrug:
        #
        # all_identifiers = Identifier.objects.all().iterator(chunk_size=20)
        # for ident in all_identifiers: ...
        # ^^^ The above code would lock up.  I think it has to do with the count taking about 10 minutes to get. ^^^

        # create the index if it doesn't exist from the schema
        if oss.index_exists() is False:
            print('index does not exist, so creating it')
            oss.create_index()

        string_parts = []
        counter = 0
        if options['starting_id']:
            start_after_id = options['starting_id']
        else:
            start_after_id = 0
        
        # Also adding additional filtering for additional criteria with a Q object that may be neutral or contain
        # time-based criteria to limit number or results.

        additional_filter = Q()  # an empty filter

        if options['updated_since']:
            updated_since = dateutil.parser.parse(options['updated_since'])
            additional_filter = Q(updateTime__gte=updated_since.timestamp())

        while True:
            # set a relatively large number to avoid going to the end
            stop_id = start_after_id + 2*DB_PAGE_SIZE
            iden_arr = (SearchIdentifier.objects.filter(id__gt=start_after_id)
                        .filter(id__lte=stop_id)
                        .filter(additional_filter).order_by('id')[:DB_PAGE_SIZE])

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
                        print(f'Error updating OpenSearch (at primary ID: {identifier.id}).')
                    else:
                        print(f'Total {counter+1} items updated in OpenSearch (at primary ID: {identifier.id}).')
                    # reset the accumulator
                    string_parts = []

                counter += 1

    def add_arguments(self, parser):
        parser.add_argument('--starting_id', type=int, nargs='?', default=0,
                            help='Starting primary ID from database (default 0)')

        parser.add_argument('--updated_since', type=str, nargs='?', default='',
                            help='Updated since date (default empty) in ISO 8601 format.'
                            ' (YYYY-MM-DDTHH:MM:SS) example: 2023-10-10T00:00:00Z.'
                            ' The date parser may support other common formats also.')

    # see https://opensearch.org/docs/latest/api-reference/document-apis/bulk/
    @staticmethod
    def _bulk_update_pair(identifier: SearchIdentifier) -> str:
        my_os = OpenSearchDoc(identifier=identifier)
        my_dict = my_os.dict_for_identifier()
        my_dict['open_search_updated'] = datetime.datetime.now().isoformat()
        line1 = json.dumps({"index": {"_index": settings.OPENSEARCH_INDEX, "_id": identifier.identifier}})
        line2 = json.dumps(my_dict)
        return f"{line1}\n{line2}"

    @staticmethod
    def _do_bulk_update(string_parts: list) -> bool:
        json_string = "\n".join(string_parts) + "\n"  # must have a trailing newline

        OpenSearchDoc.CLIENT.ping()            # OpenSearch keepalive
        response = OpenSearchDoc.CLIENT.bulk(body=json_string)

        # Check the response
        if response['errors']:
            return False
        else:
            return True




