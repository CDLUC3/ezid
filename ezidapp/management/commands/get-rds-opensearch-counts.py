#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Get identifier count from RDS and OpenSearch index
"""

import time
from django.conf import settings
import django.core.management
import ezidapp.models.identifier
from impl.open_search_doc import OpenSearchDoc


class Command(django.core.management.BaseCommand):

    def handle(self, *_, **opt):
        try:
            print("Getting OpenSearch identifier count ...")
            start_time = time.time()
            client = OpenSearchDoc.CLIENT
            response = client.count(index=settings.OPENSEARCH_INDEX)
            count_os = response['count']
            execution_time = time.time() - start_time
            print(f"OpenSearch identifier count: {count_os} (Execution time: {execution_time:.2f} seconds)")
        except Exception as ex:
            print(f"OpenSearch error: {ex}")

        try:
            print("Getting RDS Identifier count ...")
            start_time = time.time()
            # Note: objects.count() is much slower than QuerySet.count(): 340 sec vs 9 sec
            # count_id = ezidapp.models.identifier.Identifier.objects.count()
            qs_id = ezidapp.models.identifier.Identifier.objects.filter(id__gt=0)
            count_id = qs_id.count()
            execution_time = time.time() - start_time
            print(f"Identifier count: {count_id} (Execution time: {execution_time:.2f} seconds)")
            
            print("Getting RDS Search Identifier count ...")
            start_time = time.time()
            qs_sid = ezidapp.models.identifier.SearchIdentifier.objects.filter(id__gt=0)
            count_sid = qs_sid.count()
            execution_time = time.time() - start_time
            print(f"Search Identifier count: {count_sid} (Execution time: {execution_time:.2f} seconds)")
        except Exception as ex:
            print(f"Database error: {ex}")

        if count_os == count_id and count_id == count_sid:
            print("INFO: OpenSearch, Identifer and Search Identifier counts matched.")
        else:
            print("WARN: OpenSearch, Identifer and Search Identifier counts did not match.") 
        
        print("INFO: It is recommended to run this script while the EZID service is stopped.")


