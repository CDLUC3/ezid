from django.core.management.base import BaseCommand
from django.conf import settings
from ezidapp.models.identifier import SearchIdentifier
from impl.open_search_doc import OpenSearchDoc
import impl.open_search_schema as oss
import time
import datetime

import argparse

# examples of usage:
# python manage.py opensearch-utils copy_index --source source_index --destination destination_index
# python manage.py opensearch-utils update_index --source source_index --destination destination_index --updated_since 2023-10-10T00:00:00Z
# python manage.py opensearch-utils create_alias --index index_name --alias alias_name
# python manage.py opensearch-utils delete_index --index index_name

def _poll_for_completion(task_id):
    print(f'Task started with ID: {task_id}')

    start_time = time.time()

    while True:
        task_status = OpenSearchDoc.CLIENT.tasks.get(task_id=task_id)
        elapsed_time = datetime.timedelta(seconds=int(time.time() - start_time))
        if task_status['completed']:
            print(f'Task completed in {elapsed_time}.')
            break
        else:
            print(f'Task in progress... Elapsed time: {elapsed_time}')
            time.sleep(10)  # Poll every 10 seconds


class Command(BaseCommand):
    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='subcommand')

        # Subcommand: copy_index
        copy_index_parser = subparsers.add_parser('copy_index')
        copy_index_parser.add_argument('--source', type=str, required=True, help='Source index name')
        copy_index_parser.add_argument('--destination', type=str, required=True, help='Destination index name')

        # Subcommand: update_index
        update_index_parser = subparsers.add_parser('update_index')
        update_index_parser.add_argument('--source', type=str, required=True, help='Source index name')
        update_index_parser.add_argument('--destination', type=str, required=True, help='Destination index name')
        update_index_parser.add_argument('--updated_since', type=str, nargs='?', default='', help='Updated since date in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)')

        # Subcommand: create_alias
        create_alias_parser = subparsers.add_parser('create_alias')
        create_alias_parser.add_argument('--index', type=str, required=True, help='Index name')
        create_alias_parser.add_argument('--alias', type=str, required=True, help='Alias name')

        # Subcommand: delete_index
        delete_index_parser = subparsers.add_parser('delete_index')
        delete_index_parser.add_argument('--index', type=str, required=True, help='Index name')

    def handle(self, *args, **options):
        subcommand = options.pop('subcommand')

        if subcommand == 'copy_index':
            self.copy_index(**options)
        elif subcommand == 'update_index':
            self.update_index(**options)
        elif subcommand == 'create_alias':
            self.create_alias(**options)
        elif subcommand == 'delete_index':
            self.delete_index(**options)
        else:
            self.stdout.write(self.style.ERROR('Invalid subcommand'))

    @staticmethod
    def copy_index(source, destination, **options):
        # Implement the logic for copying an index
        if oss.index_exists(index_name=destination) is True:
            print('Destination index already exists, so no action was taken.')
            return

        # Create the schema for the destination index
        oss.create_index(index_name=destination)

        # Reindex from source to destination
        body = {
            "source": {
                "index": source
            },
            "dest": {
                "index": destination
            }
        }

        print(f'Indexing started at {datetime.datetime.now().isoformat()}')
        response = OpenSearchDoc.CLIENT.reindex(body=body, wait_for_completion=False)
        task_id = response['task']

        _poll_for_completion(task_id=task_id)

    @staticmethod
    def update_index(source, destination, updated_since, **options):
        # Check if the destination index exists
        if not oss.index_exists(index_name=destination):
            print('Destination index does not exist.')
            return

        print(f'Indexing started at {datetime.datetime.now().isoformat()}')

        # Reindex from source to destination with a query to filter documents
        body = {
            "source": {
                "index": source,
                "query": {
                    "range": {
                        "open_search_updated": {
                            "gte": updated_since
                        }
                    }
                }
            },
            "dest": {
                "index": destination
            }
        }

        response = OpenSearchDoc.CLIENT.reindex(body=body, wait_for_completion=False)
        task_id = response['task']

        _poll_for_completion(task_id=task_id)

    @staticmethod
    def delete_index(index, **options):
        # Check if the destination index exists
        if not oss.index_exists(index_name=index):
            print('Index does not exist.')
            return

        print(f'Deleting index {index} started at {datetime.datetime.now().isoformat()}')
        response = OpenSearchDoc.CLIENT.indices.delete(index=index) # Delete the index
        print(f'Index {index} deleted successfully.')


    @staticmethod
    def create_alias(index, alias, **options):
        # Check if the destination index exists
        if not oss.index_exists(index_name=index):
            print('Index does not exist.')
            return

        print(f'Creating alias {alias} for index {index} started at {datetime.datetime.now().isoformat()}')
        response = OpenSearchDoc.CLIENT.indices.put_alias(index=index, name=alias)
        print(f'Alias {alias} created successfully.')


