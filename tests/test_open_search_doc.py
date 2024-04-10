import pytest
import responses
from unittest.mock import Mock
from unittest.mock import MagicMock
from ezidapp.models.identifier import Identifier
from impl.open_search_doc import OpenSearchDoc


@pytest.fixture
def open_search_doc():
    # Create a mock Identifier object
    identifier = MagicMock(spec=Identifier)

    # mocking out the meta object for the Identifier database object
    meta = MagicMock()
    field_names = 'id identifier createTime updateTime status unavailableReason exported crossrefStatus' \
        ' crossrefMessage target cm agentRole isTest datacenter_id owner_id ownergroup_id ' \
        'profile_id metadata'.split()

    fields = []
    for field in field_names:
        f = MagicMock()
        f.name = field
        fields.append(f)

    meta.fields = fields

    identifier._meta = meta
    identifier.id = 37
    identifier.pk = 37
    identifier.createTime = 1640995200
    identifier.updateTime = 1640998666
    identifier.status = 'P'
    identifier.unavailableReason = ''
    identifier.crossrefStatus = ''
    identifier.crossrefMessage = ''
    identifier.cm = 'meow'
    identifier.agentRole = ''
    identifier.datacenter_id = 266
    identifier.owner_id = 22
    identifier.ownergroup_id = 33
    identifier.profile_id = 44
    identifier.metadata = {'json': 'metadata'}

    identifier.identifier = 'doi:10.25338/B8JG7X'
    identifier.target = 'http://example.com'
    identifier.defaultTarget = 'http://default.com'
    identifier.isDatacite = False
    identifier.isPublic = True
    identifier.exported = True
    identifier.isTest = False

    identifier.owner = MagicMock()
    identifier.owner.username = 'testuser'
    identifier.owner.displayName = 'Test User'
    identifier.owner.accountEmail = 'test.user@example.org'
    identifier.owner.id = 22

    identifier.ownergroup = MagicMock()
    identifier.ownergroup.id = 33
    identifier.ownergroup.groupname = 'testgroup'
    identifier.ownergroup.organizationName = 'Test Organization'

    identifier.profile = MagicMock()
    identifier.profile.id = 44
    identifier.profile.label = 'testprofile'

    identifier.metadata = {}

    # Create a mock KernelMetadata object
    km = Mock()
    km.creator = 'Test Creator'
    km.title = 'Test Title'
    km.publisher = 'Test Publisher'
    km.date = '2022-01-01'
    km.type = 'Dataset/dataset'
    km.validatedDate = '2022'
    km.validatedType = 'Dataset/dataset'

    identifier.kernelMetadata = km

    # Create the OpenSearchDoc object to test
    return OpenSearchDoc(identifier=identifier)


def test_searchable_target(open_search_doc):
    assert open_search_doc.searchable_target == 'moc.elpmaxe//:ptth'


def test_resource_creator(open_search_doc):
    assert open_search_doc.resource_creator == 'Test Creator'


def test_resource_creators(open_search_doc):
    assert open_search_doc.resource_creators == ['Test Creator']


def test_resource_title(open_search_doc):
    assert open_search_doc.resource_title == 'Test Title'


def test_resource_publisher(open_search_doc):
    assert open_search_doc.resource_publisher == 'Test Publisher'


def test_resource_publication_date(open_search_doc):
    assert open_search_doc.resource_publication_date == '2022-01-01'


def test_resource(open_search_doc):
    expected_resource = {'creators': ['Test Creator'],
                         'title': 'Test Title',
                         'publisher': 'Test Publisher',
                         'publication_date': '2022-01-01',
                         'type': 'Dataset/dataset'}
    assert open_search_doc.resource == expected_resource


def test_owner(open_search_doc):
    expected_owner = {'id': 22,
                      'username': 'testuser',
                      'display_name': 'Test User',
                      'account_email': 'test.user@example.org'}
    assert open_search_doc.owner == expected_owner


def test_ownergroup(open_search_doc):
    expected_ownergroup = {'id': 33, 'name': 'testgroup', 'organization': 'Test Organization'}
    assert open_search_doc.ownergroup == expected_ownergroup


def test_profile(open_search_doc):
    expected_profile = {'id': 44, 'label': 'testprofile'}
    assert open_search_doc.profile == expected_profile


def test_searchable_publication_year(open_search_doc):
    assert open_search_doc.searchable_publication_year == 2022


def test_resource_type(open_search_doc):
    assert open_search_doc.resource_type == 'Dataset/dataset'


def test_searchable_resource_type(open_search_doc):
    assert open_search_doc.searchable_resource_type == 'D'


def test_word_bucket(open_search_doc):
    expected_word_bucket = 'doi:10.25338/B8JG7X ; testuser ; testgroup ; http://example.com'
    assert open_search_doc.word_bucket == expected_word_bucket


def test_resource_creator_prefix(open_search_doc):
    assert open_search_doc.resource_creator_prefix == 'Test Creator'


def test_resource_title_prefix(open_search_doc):
    assert open_search_doc.resource_title_prefix == 'Test Title'


def test_resource_publisher_prefix(open_search_doc):
    assert open_search_doc.resource_publisher_prefix == 'Test Publisher'


def test_has_metadata(open_search_doc):
    assert open_search_doc.has_metadata


def test_public_search_visible(open_search_doc):
    assert open_search_doc.public_search_visible


def test_oai_visible(open_search_doc):
    assert open_search_doc.oai_visible


def test_dict_for_identifier(open_search_doc):
    expected_dict = {'id': 'doi:10.25338/B8JG7X',
                     'create_time': '2022-01-01T00:00:00',
                     'update_time': '2022-01-01T00:57:46',
                     'status': 'P',
                     'unavailable_reason': '',
                     'exported': True,
                     'crossref_status': '',
                     'crossref_message': '',
                     'target': 'http://example.com',
                     'agent_role': '',
                     'is_test': False,
                     'datacenter_id': 266,
                     'db_identifier_id': 37,
                     'resource': {
                         'creators': ['Test Creator'],
                         'title': 'Test Title',
                         'publisher': 'Test Publisher',
                         'publication_date': '2022-01-01',
                         'type': 'Dataset/dataset'},
                     'word_bucket': 'doi:10.25338/B8JG7X ; testuser ; testgroup ; http://example.com',
                     'has_metadata': True,
                     'public_search_visible': True,
                     'oai_visible': True,
                     'owner': {
                         'id': 22,
                         'username': 'testuser',
                         'display_name': 'Test User',
                         'account_email': 'test.user@example.org'},
                     'ownergroup': {'id': 33, 'name': 'testgroup', 'organization': 'Test Organization'},
                     'profile': {'id': 44, 'label': 'testprofile'}}
    assert open_search_doc.dict_for_identifier() == expected_dict

@responses.activate
def test_index_exists(open_search_doc):
    url = 'http://opensearch.example.com/ezid-test-index'

    # Define the response you want to return
    responses.add(responses.HEAD, url, status=200)

    result = open_search_doc.index_exists()

    assert result

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == url
