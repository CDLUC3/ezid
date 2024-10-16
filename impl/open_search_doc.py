from django.core.serializers import serialize
from django.http import JsonResponse

# import settings.settings
from django.conf import settings
from django.test import override_settings
from ezidapp.models.identifier import Identifier
from ezidapp.models.identifier import SearchIdentifier
import json
import base64
import datetime
import ezidapp.models.validation as validation
import impl.util
from urllib.parse import quote
import re
import functools
from opensearchpy import OpenSearch
from opensearchpy.exceptions import NotFoundError
from django.conf import settings
import urllib

# the functools allows memoizing the results of functions, so they're not recalculated every time (ie cached
# results if called more than once on the same instance)

MAX_SEARCHABLE_TARGET_LENGTH = 255
INDEXED_PREFIX_LENGTH = 50

# testing
# python manage.py shell

# seems like they're using the django db model libraries https://docs.djangoproject.com/en/5.0/topics/db/queries/

"""
-- basic testing -- in "python manage.py shell"
from impl.open_search_doc import OpenSearchDoc
from ezidapp.models.identifier import SearchIdentifier
open_s = OpenSearchDoc(identifier=SearchIdentifier.objects.get(identifier='doi:10.25338/B8JG7X'))
my_dict = open_s.dict_for_identifier()
open_s.index_document()
"""

# do we really need the crossref status and message which seem like internal fields for EZID maintenance, not search ?
class OpenSearchDoc:
    PARSED_URL = urllib.parse.urlparse(settings.OPENSEARCH_BASE)
    CLIENT = OpenSearch(
        hosts=[{'host': PARSED_URL.hostname, 'port': PARSED_URL.port}],
        http_compress=True,  # enables gzip compression for request bodies
        http_auth=(settings.OPENSEARCH_USER, settings.OPENSEARCH_PASSWORD),
        use_ssl=True,
        verify_certs=True,
        ssl_assert_hostname=False,
        ssl_show_warn=False
    )

    def __init__(self, identifier: Identifier):
        self.identifier = identifier
        self.km = identifier.kernelMetadata

        try:
            self.search_identifier=SearchIdentifier.objects.get(identifier=identifier.identifier)
        except SearchIdentifier.DoesNotExist:
            self.search_identifier=None

    # convenience method to index a document from an identifier
    @staticmethod
    def index_from_identifier(identifier):
        open_s = OpenSearchDoc(identifier=identifier)
        return open_s.index_document()

    # class convenience method to index a document from a search identifier, likely can be removed in the future
    # when we get rid of the search identifier table
    @staticmethod
    def index_from_search_identifier(search_identifier):
        identifier = Identifier.objects.get(identifier=search_identifier.identifier)
        open_s = OpenSearchDoc(identifier=identifier)
        return open_s.index_document()

    # class convenience method to index a document from a search identifier, likely can be removed in the future
    # when we get rid of the search identifier table
    @staticmethod
    def delete_from_search_identifier(search_identifier):
        identifier = Identifier.objects.get(identifier=search_identifier.identifier)
        open_s = OpenSearchDoc(identifier=identifier)
        return open_s.remove_from_index()

    # uphold Python conventions and make fields snake_case instead of initial lower camelCase
    @staticmethod
    def _camel_to_snake(name):
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

    def dict_for_identifier(self) -> str:
        identifier_dict = {}
        exclude_fields = "pk cm metadata owner_id ownergroup_id profile_id datacenter_id".split()
        for field in self.identifier._meta.fields:
            if field.name not in exclude_fields:
                field_name = OpenSearchDoc._camel_to_snake(field.name)
                field_value = getattr(self.identifier, field.name)
                if field_value is None:
                    field_value = ''

                if hasattr(field_value, 'pk'):  # Check if it's a foreign key
                    tmp = field_value.pk
                elif isinstance(field_value, bytes):
                    tmp = base64.b64encode(field_value).decode('utf-8')
                elif field.name.endswith('Time'):
                    tmp = datetime.datetime.utcfromtimestamp(field_value).isoformat()
                else:
                    tmp = field_value
                identifier_dict[field_name] = tmp

        fields_to_add = ['db_identifier_id', 'resource', 'word_bucket', 'has_metadata', 'public_search_visible',
                         'oai_visible', 'owner', 'ownergroup', 'profile', 'datacenter', 'identifier_type',
                         'searchable_publication_year', 'searchable_id', 'link_is_broken', 'has_issues']

        for field in fields_to_add:
            identifier_dict[field] = getattr(self, f'{field}')

        identifier_dict.pop('identifier')
        identifier_dict['id'] = self.identifier.identifier

        # linkIsBroken, hasIssue fields remain in the Searchidentifiers table and when we are ready to remove most data
        # from the searchidentifiers table, we can either remove unused columns from that table or else move these fields
        # into a different database table/model.

        return identifier_dict

    def remove_from_index(self):
        try:
            response = self.CLIENT.delete(
                index=settings.OPENSEARCH_INDEX,
                id=self.identifier.identifier,
            )
            if response['result'] == 'deleted':
                return True
        except NotFoundError:
            # if it's not found, it's already deleted
            return True
        return False

    def update_link_issues(self, link_is_broken=False, has_issues=False):
        dict_to_update = {
            'open_search_updated': datetime.datetime.now().isoformat(),
            'update_time': datetime.datetime.now().isoformat(),
            'link_is_broken': link_is_broken,
            'has_issues': has_issues }

        response = self.CLIENT.update(
            index=settings.OPENSEARCH_INDEX,
            id=self.identifier.identifier,
            body={"doc": dict_to_update}
        )

        # Check the response
        if 'result' in response and response['result'] == 'updated':
            return True
        else:
            return False

    # the properties using lru_cache are memoized, so they're only calculated once and then cached for future calls
    # for the same object instance (this should make calls faster if used multiple times on the same instance)

    @property
    @functools.lru_cache
    def db_identifier_id(self):
        return self.identifier.pk

    # these are builder functions for the parts of the search
    @property
    @functools.lru_cache
    def searchable_target(self):
        return self.identifier.target[::-1][:MAX_SEARCHABLE_TARGET_LENGTH]

    @property
    @functools.lru_cache
    def resource(self):
        return {"creators": self.resource_creators,
                "title": self.resource_title,
                "publisher": self.resource_publisher,
                "publication_date": self.resource_publication_date,
                "type": self.resource_type,
                "type_words": self.resource_type_words,
                "searchable_type": self.searchable_resource_type}

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

    # this one is indexed as "keyword" so I can do a "prefix" search against it since otherwise it doesn't work
    @property
    @functools.lru_cache
    def searchable_id(self):
        return self.identifier.identifier

    @property
    @functools.lru_cache
    def link_is_broken(self):
        if self.search_identifier is not None:
            return self.search_identifier.linkIsBroken
        return False

    @property
    @functools.lru_cache
    def has_issues(self):
        if self.search_identifier is not None:
            return self.search_identifier.hasIssues
        return False

    @property
    @functools.lru_cache
    def resource_type(self):
        return self.km.type if self.km.type is not None else ''

    @property
    @functools.lru_cache
    def searchable_resource_type(self):
        t = self.km.validatedType
        return validation.resourceTypes[t.split("/")[0]] if t is not None else ''

    # The resource types have changed over time and different Datacite versions.
    # It also seems like the expectation is that we have the most inclusive match
    # on the resource type terms in search if anything related has been entered anywhere in resource type.
    # This gloms all the words in that are present in the "validatedType" for full text searching.
    # First it splits out words on whitespace, underscore, dash, and slash.
    # Then it adds additional words for anything CamelCased to get the most inclusive words possible.
    @property
    @functools.lru_cache
    def resource_type_words(self):
        t = self.km.validatedType
        if t is None or t == "":
            return None

        # split on whitespace, underscore, dash, and slash
        obvious_words = re.split(r'[\s_\-/]+', t)

        more_words = []
        for word in obvious_words:
            # Insert a space before each uppercase letter
            spaced_text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', word)
            # Split the string on spaces
            extra_words = spaced_text.split()
            if len(extra_words) > 1:
                more_words.extend(extra_words)

        return ' '.join(obvious_words + more_words)  # a bucket of words for search

    @property
    @functools.lru_cache
    def word_bucket(self):
        kw = [self.identifier.identifier,
              self.identifier.owner.username if self.identifier.owner else None,
              self.identifier.ownergroup.groupname if self.identifier.ownergroup else None]
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
        kw = [x for x in kw if x is not None]
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

    @property
    @functools.lru_cache
    def owner(self):
        o = self.identifier.owner
        if o is None:
            return {}
        return {"id": o.id, "username": o.username, "display_name": o.displayName, "account_email": o.accountEmail}

    # adds a subset of the ownergroup, the id, name, and organization.  I'm cautious about adding too much data
    # to the search in case it's not needed for search
    @property
    @functools.lru_cache
    def ownergroup(self):
        og = self.identifier.ownergroup
        if og is None:
            return {}
        return {"id": og.id, "name": og.groupname, "organization": og.organizationName}

    @property
    @functools.lru_cache
    def profile(self):
        p = self.identifier.profile
        if p is None:
            return {}
        return {"id": p.id, "label": p.label}

    @property
    @functools.lru_cache
    def datacenter(self):
        dc = self.identifier.datacenter
        if dc is None:
            return {"id": None, "symbol": "", "name": ""}
        return {"id": dc.id, "symbol": dc.symbol, "name": dc.name}

    # identifier_type is ark or doi and the db search did some kind of slow like query for it, but should be explicit
    @property
    @functools.lru_cache
    def identifier_type(self):
        if self.identifier.identifier and self.identifier.identifier.startswith("doi:"):
            return "doi"
        return "ark"

    @classmethod
    def index_exists(cls, index_name=settings.OPENSEARCH_INDEX):
        return OpenSearchDoc.CLIENT.indices.exists(index=index_name)

    def index_document(self):
        os_doc = self.dict_for_identifier()
        os_doc['open_search_updated'] = datetime.datetime.now().isoformat()

        # Use the index method of the OpenSearch client to index the document
        response = self.CLIENT.index(
            index=settings.OPENSEARCH_INDEX,
            id=self.identifier.identifier,
            body=os_doc,
        )

        # Check the response
        if 'result' in response and response['result'] in ['created', 'updated']:
            return True
        else:
            return False
