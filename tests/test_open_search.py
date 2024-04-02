import pytest
import responses
from unittest.mock import Mock
from ezidapp.models.identifier import Identifier
from impl.open_search import OpenSearch

@pytest.fixture
def open_search():
    # Create a mock Identifier object
    identifier = Mock(spec=Identifier)
    identifier.identifier = 'doi:10.25338/B8JG7X'
    identifier.target = 'http://example.com'
    identifier.defaultTarget = 'http://default.com'
    identifier.isDatacite = False
    identifier.isPublic = True
    identifier.exported = True
    identifier.isTest = False
    identifier.owner = Mock()
    identifier.owner.username = 'testuser'
    identifier.ownergroup = Mock()
    identifier.ownergroup.groupname = 'testgroup'
    identifier.metadata = {}

    # Create a mock KernelMetadata object
    km = Mock()
    km.creator = 'Test Creator'
    km.title = 'Test Title'
    km.publisher = 'Test Publisher'
    km.date = '2022-01-01'
    km.type = 'Test Type'
    km.validatedDate = '2022'
    km.validatedType = 'Dataset/dataset'

    identifier.kernelMetadata = km

    # Create the OpenSearch object to test
    return OpenSearch(identifier)

def test_searchable_target(open_search):
    assert open_search.searchable_target == 'moc.elpmaxe//:ptth'

def test_resource_creator(open_search):
    assert open_search.resource_creator == 'Test Creator'

def test_resource_creators(open_search):
    assert open_search.resource_creators == ['Test Creator']

def test_resource_title(open_search):
    assert open_search.resource_title == 'Test Title'

def test_resource_publisher(open_search):
    assert open_search.resource_publisher == 'Test Publisher'

def test_resource_publication_date(open_search):
    assert open_search.resource_publication_date == '2022-01-01'

def test_searchable_publication_year(open_search):
    assert open_search.searchable_publication_year == 2022

def test_resource_type(open_search):
    assert open_search.resource_type == 'Test Type'

def test_searchable_resource_type(open_search):
    assert open_search.searchable_resource_type == 'D'

def test_word_bucket(open_search):
    expected_word_bucket = 'doi:10.25338/B8JG7X ; testuser ; testgroup ; http://example.com'
    assert open_search.word_bucket == expected_word_bucket

def test_resource_creator_prefix(open_search):
    assert open_search.resource_creator_prefix == 'Test Creator'

def test_resource_title_prefix(open_search):
    assert open_search.resource_title_prefix == 'Test Title'

def test_resource_publisher_prefix(open_search):
    assert open_search.resource_publisher_prefix == 'Test Publisher'

def test_has_metadata(open_search):
    assert open_search.has_metadata

def test_public_search_visible(open_search):
    assert open_search.public_search_visible

def test_oai_visible(open_search):
    assert open_search.oai_visible

@responses.activate
def test_index_exists(open_search):
    url = 'http://opensearch.example.com/ezid-test-index'

    # Define the response you want to return
    responses.add(responses.HEAD, url, status=200)

    result = open_search.index_exists()

    assert result

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == url
