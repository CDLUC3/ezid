import pytest
from unittest.mock import Mock, patch, ANY
from unittest.mock import MagicMock
from ezidapp.models.identifier import Identifier
from ezidapp.models.identifier import SearchIdentifier
from impl.open_search_doc import OpenSearchDoc
from unittest.mock import patch


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

    identifier.datacenter = MagicMock()
    identifier.datacenter.id = 266
    identifier.datacenter.symbol = 'CDL.CDL'
    identifier.datacenter.name = 'California Digital Library'

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

    # The search_identifier is only used to get a subset of the columns.
    #
    search_identifier = MagicMock(spec=SearchIdentifier)
    search_identifier.identifier = identifier.identifier
    search_identifier.hasIssues = False
    search_identifier.linkIsBroken = False
    identifier.search_identifier = search_identifier

    # hope this works to patch the mock call in the OpenSearchDoc initializer
    with patch('ezidapp.models.identifier.SearchIdentifier.objects.get', return_value=search_identifier) as mock_get:
        # Create an OpenSearchDoc object
        open_search_doc = OpenSearchDoc(identifier=identifier)

    # Create the OpenSearchDoc object to test
    return open_search_doc


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
                         'type': 'Dataset/dataset',
                         'searchable_type': 'D'}
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


def test_resource_type_words(open_search_doc):
    assert open_search_doc.resource_type_words == 'Dataset dataset'


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


def test_identifier_type(open_search_doc):
    assert open_search_doc.identifier_type == 'doi'


def searchable_publication_year(open_search_doc):
    assert open_search_doc.searchable_publication_year == 2022


def searchable_id(open_search_doc):
    assert open_search_doc.searchable_id == 'doi:10.25338/B8JG7X'


def link_is_broken(open_search_doc):
    assert open_search_doc.link_is_broken is False


def has_issues(open_search_doc):
    assert open_search_doc.has_issues is False


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
                     'datacenter': {
                        'id': 266,
                        'symbol': 'CDL.CDL',
                        'name': 'California Digital Library'
                     },
                     'db_identifier_id': 37,
                     'resource': {
                         'creators': ['Test Creator'],
                         'title': 'Test Title',
                         'publisher': 'Test Publisher',
                         'publication_date': '2022-01-01',
                         'type': 'Dataset/dataset',
                         'searchable_type': 'D'},
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
                     'profile': {'id': 44, 'label': 'testprofile'},
                     'identifier_type': 'doi',
                     'searchable_publication_year': 2022,
                     'searchable_id': 'doi:10.25338/B8JG7X',
                     'link_is_broken': False,
                     'has_issues': False}
    assert open_search_doc.dict_for_identifier() == expected_dict


@patch('impl.open_search_doc.OpenSearchDoc.CLIENT')
def test_update_link_issues(mock_client, open_search_doc):
    # Arrange
    mock_response = {'result': 'updated'}
    mock_client.update.return_value = mock_response

    # Act
    result = open_search_doc.update_link_issues(link_is_broken=True, has_issues=True)

    # Assert
    mock_client.update.assert_called_once_with(
        index='ezid-test-index',
        id=open_search_doc.identifier.identifier,
        body={"doc": {
            'open_search_updated': ANY,  # Use unittest.mock.ANY if the exact value doesn't matter
            'update_time': ANY,
            'link_is_broken': True,
            'has_issues': True
        }}
    )
    assert result is True

