from django.core.management.base import BaseCommand
from django.conf import settings
from ezidapp.models.identifier import SearchIdentifier
from impl.open_search_doc import OpenSearchDoc
import json
from django.db import connection



# this is only for the time being since I'm using a local server without correct SSL/https
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Disable only the InsecureRequestWarning
urllib3.disable_warnings(InsecureRequestWarning)
# end suppression of urllib3 InsecureRequestWarning

SPLIT_SIZE = 100

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
        # iterate through all items in the OpenSearch index and check against the database
        # SearchIdentifier table to find removed items and remove them from the index

        # Initialize the OpenSearch client
        client = OpenSearchDoc.CLIENT
        index_name=settings.OPENSEARCH_INDEX

        # Start the scroll
        response = client.search(
            index=index_name,
            body={
                "query": {
                    "match_all": {}
                }
            },
            scroll='2m',  # Keep the scroll context alive for 2 minutes
            size=100  # Number of results per batch
        )

        # Extract the scroll ID and the initial batch of results
        scroll_id = response['_scroll_id']
        hits = response['hits']['hits']

        checked_count = 100

        # Continue scrolling until no more results are returned
        while len(hits) > 0:
            ids = [hit['_id'] for hit in hits]

            # Make a left join query which should be efficient for getting a list of items that are in the index but
            # not in the database. MySQL makes it more complicated because it doesn't support FROM VALUES.

            # Convert the list of identifiers to a string format suitable for SQL.  This UNION ALL is janky as hell
            # but MySQL doesn't support FROM VALUES. The other option was to create a temporary table every time, but
            # that seemed like overkill.
            ids_union = ' UNION ALL '.join(f"SELECT '{identifier}' AS identifier" for identifier in ids)

            # Raw SQL query to find identifiers in the list that are not in the database
            query = f"""
                SELECT id_list.identifier
                FROM ({ids_union}) AS id_list
                LEFT JOIN ezidapp_searchidentifier AS si ON id_list.identifier = si.identifier
                WHERE si.identifier IS NULL;
            """

            # Execute the query
            with connection.cursor() as cursor:
                cursor.execute(query)
                missing_identifiers = [row[0] for row in cursor.fetchall()]

            missing_identifiers_list = list(missing_identifiers)

            if len(missing_identifiers_list) > 0:
                # Create the bulk delete request payload
                bulk_delete_payload = ""
                for identifier in missing_identifiers_list:
                    bulk_delete_payload += json.dumps(
                        {"delete": {"_index": index_name, "_id": identifier}}) + "\n"

                # Send the bulk delete request to OpenSearch
                response = client.bulk(body=bulk_delete_payload)

                # Check the response
                if response['errors']:
                    print(f"  Errors occurred during bulk delete of {missing_identifiers_list.join(', ')}")
                else:
                    print(f"  Bulk delete successful deleting {missing_identifiers_list.join(', ')}")

            print("checked:", checked_count)

            response = client.scroll(
                scroll_id=scroll_id,
                scroll='2m'
            )

            scroll_id = response['_scroll_id']
            hits = response['hits']['hits']
            checked_count += len(hits)

        # Clear the scroll context
        client.clear_scroll(scroll_id=scroll_id)
        print("Done removing deleted IDs")
