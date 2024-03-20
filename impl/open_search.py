from django.core.serializers import serialize
from django.http import JsonResponse
from ezidapp.models.identifier import Identifier
import json
import pdb
import base64
import datetime
import ezidapp.models.validation as validation
import impl.util

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
my_json = open_s.json_for_identifier()
"""

# todo: Do we need more meaningful values for these fields or are the database IDs ok?
# datacenter, profile, owner, ownergroup
# also, do we really need the crossref status and message which seem like internal fields for EZID maintenance, not search
class OpenSearch:
    def __init__(self, identifier: Identifier):
        self.identifier = identifier
        self.km = identifier.kernelMetadata

    def json_for_identifier(self) -> str:
        identifier_dict = {}
        exclude_fields = "pk cm metadata".split()
        for field in self.identifier._meta.fields:
            if field.name not in exclude_fields:
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
                identifier_dict[field.name] = tmp

        fields_to_add = ['resource_creators', 'resource_title', 'resource_publisher',
                         'resource_publication_date', 'resource_type',
                         'word_bucket', 'has_metadata', 'public_search_visible', 'oai_visible']

        for field in fields_to_add:
            identifier_dict[field] = getattr(self, f'_{field}')()

        # need to add linkIsBroken, hasIssue ?

        return json.dumps(identifier_dict, indent=2)

    # these are builders for the parts of the search
    def _searchable_target(self):
        return self.identifier.target[::-1][:MAX_SEARCHABLE_TARGET_LENGTH]

    def _resource_creator(self):
        return self.km.creator if self.km.creator is not None else ''

    def _resource_creators(self):
        if self.km.creator is None:
            return []
        creators = self.km.creator.split(';')
        return [c.strip() for c in creators]

    def _resource_title(self):
        return self.km.title if self.km.title is not None else ''

    def _resource_publisher(self):
        return self.km.publisher if self.km.publisher is not None else ''

    def _resource_publication_date(self):
        return self.km.date if self.km.date is not None else ''

    def _searchable_publication_year(self):
        d = self.km.validatedDate
        return int(d[:4]) if d is not None else None

    def _resource_type(self):
        return self.km.type if self.km.type is not None else ''

    def _searchable_resource_type(self):
        t = self.km.validatedType
        return validation.resourceTypes[t.split("/")[0]] if t is not None else ''

    def _word_bucket(self):
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

    def _resource_creator_prefix(self):
        return self._resource_creator()[: INDEXED_PREFIX_LENGTH]

    def _resource_title_prefix(self):
        return self._resource_title()[: INDEXED_PREFIX_LENGTH]

    def _resource_publisher_prefix(self):
        return self._resource_publisher()[: INDEXED_PREFIX_LENGTH]

    def _has_metadata(self):
        return (
            self._resource_title() != ""
            and self._resource_publication_date() != ""
            and (self._resource_creator() != "" or self._resource_publisher() != "")
        )

    def _public_search_visible(self):
        return self.identifier.isPublic and self.identifier.exported and not self.identifier.isTest

    def _oai_visible(self):
        return (
            self._public_search_visible() and self._has_metadata() and self.identifier.target != self.identifier.defaultTarget
        )