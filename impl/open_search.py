from django.core.serializers import serialize
from django.http import JsonResponse

import settings.settings
from ezidapp.models.identifier import Identifier
import json
import pdb
import base64
import datetime
import ezidapp.models.validation as validation
import impl.util
import requests
from django.conf import settings
from urllib.parse import quote
import re
import functools

# the functools allows memoizing the results of functions so they're not recalculated every time (ie cached
# results if called more than once on the same instance)

MAX_SEARCHABLE_TARGET_LENGTH = 255
INDEXED_PREFIX_LENGTH = 50

# testing
# python manage.py shell

# seems like they're using the django db model libraries https://docs.djangoproject.com/en/5.0/topics/db/queries/

"""
-- basic testing
import impl.open_search as os
from ezidapp.models.identifier import Identifier
open_s = os.OpenSearch(identifier=Identifier.objects.get(identifier='doi:10.25338/B8JG7X'))
my_dict = open_s.dict_for_identifier()
"""

# todo: Do we need more meaningful values for these fields or are the database IDs ok?
# datacenter, profile, owner, ownergroup
# also, do we really need the crossref status and message which seem like internal fields for EZID maintenance, not search
class OpenSearch:
    def __init__(self, identifier: Identifier):
        self.identifier = identifier
        self.km = identifier.kernelMetadata

    # someone broke Python conventions and wrote some fields as camelCase instead of snake_case, so don't want to
    # propagate it further
    def _camel_to_snake(name):
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

    def dict_for_identifier(self) -> str:
        identifier_dict = {}
        exclude_fields = "pk cm metadata".split()
        for field in self.identifier._meta.fields:
            if field.name not in exclude_fields:
                field_name = OpenSearch._camel_to_snake(field.name)
                field_value = getattr(self.identifier, field.name)
                if field_value is None:
                    field_value = ''

                # this fugly construct because . . . python
                if hasattr(field_value, 'pk'):  # Check if it's a foreign key
                    tmp = field_value.pk
                elif isinstance(field_value, bytes):
                    tmp = base64.b64encode(field_value).decode('utf-8')
                elif field.name.endswith('Time'):
                    tmp = datetime.datetime.utcfromtimestamp(field_value).isoformat()
                else:
                    tmp = field_value
                identifier_dict[field_name] = tmp

        fields_to_add = ['resource_creators', 'resource_title', 'resource_publisher',
                         'resource_publication_date', 'resource_type',
                         'word_bucket', 'has_metadata', 'public_search_visible', 'oai_visible']

        for field in fields_to_add:
            identifier_dict[field] = getattr(self, f'{field}')

        identifier_dict.pop('identifier')
        identifier_dict['id'] = self.identifier.identifier

        # need to add linkIsBroken, hasIssue ?

        # return json.dumps(identifier_dict, indent=2) # need to add additional things to this dict for insertions/updates
        return identifier_dict

    # these are builders for the parts of the search
    @property
    @functools.lru_cache
    def searchable_target(self):
        return self.identifier.target[::-1][:MAX_SEARCHABLE_TARGET_LENGTH]

    @property
    @functools.lru_cache
    def resource_creator(self):
        return self.km.creator if self.km.creator is not None else ''

    @property
    @functools.lru_cache
    def resource_creators(self):
        if self.km.creator is None:
            return []
        creators = self.km.creator.split(';')
        return [c.strip() for c in creators]

    @property
    @functools.lru_cache
    def resource_title(self):
        return self.km.title if self.km.title is not None else ''

    @property
    @functools.lru_cache
    def resource_publisher(self):
        return self.km.publisher if self.km.publisher is not None else ''

    @property
    @functools.lru_cache
    def resource_publication_date(self):
        return self.km.date if self.km.date is not None else ''

    @property
    @functools.lru_cache
    def searchable_publication_year(self):
        d = self.km.validatedDate
        return int(d[:4]) if d is not None else None

    @property
    @functools.lru_cache
    def resource_type(self):
        return self.km.type if self.km.type is not None else ''

    @property
    @functools.lru_cache
    def searchable_resource_type(self):
        t = self.km.validatedType
        return validation.resourceTypes[t.split("/")[0]] if t is not None else ''

    @property
    @functools.lru_cache
    def word_bucket(self):
        kw = [self.identifier.identifier, self.identifier.owner.username, self.identifier.ownergroup.groupname]
        if self.identifier.isDatacite:
            kw.append(self.identifier.datacenter.symbol)
        if self.identifier.target != self.identifier.defaultTarget:
            kw.append(self.identifier.target)
        for k, v in list(self.identifier.metadata.items()):
            if k in ["datacite", "crossref"]:
                try:
                    kw.append(impl.util.extractXmlContent(v))
                except Exception:
                    kw.append(v)
            else:
                kw.append(v)
        return " ; ".join(kw)

    @property
    @functools.lru_cache
    def resource_creator_prefix(self):
        return self.resource_creator[: INDEXED_PREFIX_LENGTH]

    @property
    @functools.lru_cache
    def resource_title_prefix(self):
        return self.resource_title[: INDEXED_PREFIX_LENGTH]

    @property
    @functools.lru_cache
    def resource_publisher_prefix(self):
        return self.resource_publisher[: INDEXED_PREFIX_LENGTH]

    @property
    @functools.lru_cache
    def has_metadata(self):
        return (
            self.resource_title != ""
            and self.resource_publication_date != ""
            and (self.resource_creator != "" or self.resource_publisher != "")
        )

    @property
    @functools.lru_cache
    def public_search_visible(self):
        return self.identifier.isPublic and self.identifier.exported and not self.identifier.isTest

    @property
    @functools.lru_cache
    def oai_visible(self):
        return (
            self.public_search_visible and self.has_metadata and self.identifier.target != self.identifier.defaultTarget
        )

    def index_exists(self):
        url = f'{settings.OPENSEARCH_BASE}/{settings.OPENSEARCH_INDEX}'
        response = requests.head(url, auth=(settings.OPENSEARCH_USER, settings.OPENSEARCH_PASSWORD), verify=False)
        # Check the response
        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False
        else:
            return None


    # it looks like I need to do this from the opensearch dashboard because of permission denied 401 errors
    def create_index(self):
        # The URL for the OpenSearch endpoint
        url = f'{settings.OPENSEARCH_BASE}/{settings.OPENSEARCH_INDEX}'

        # The settings for the index
        index_settings = {
            "settings": {
                "index": {
                    "number_of_shards": 1,
                    "number_of_replicas": 1
                }
            }
        }

        # Convert the dictionary into a JSON string
        json_string = json.dumps(index_settings)

        # Send the PUT request
        response = requests.put(url, data=json_string, headers={'Content-Type': 'application/json'}, verify=False)

        # Check the response
        if response.status_code == 200:
            return True
        else:
            return False

    def index_document(self):
        encoded_identifier = quote(self.identifier.identifier, safe='')

        # The URL for the OpenSearch endpoint
        url = f'{settings.OPENSEARCH_BASE}/{settings.OPENSEARCH_INDEX}/_doc/{encoded_identifier}'

        # Convert the dictionary into a JSON string
        os_doc = self.dict_for_identifier()
        os_doc['open_search_updated'] = datetime.datetime.now().isoformat()

        json_string = json.dumps(os_doc)

        # Send the PUT request
        response = requests.put(url,
                                 data=json_string,
                                 headers={'Content-Type': 'application/json'},
                                 auth=(settings.OPENSEARCH_USER, settings.OPENSEARCH_PASSWORD),
                                 verify=False)

        # Check the response
        if response.status_code in range(200, 299):
            return True
        else:
            return False
