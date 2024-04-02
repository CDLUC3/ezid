import responses
import unittest
from unittest.mock import Mock
from ezidapp.models.identifier import Identifier
from impl.open_search import OpenSearch

class TestOpenSearch(unittest.TestCase):
    def setUp(self):
        # Create a mock Identifier object
        self.identifier = Mock(spec=Identifier)
        self.identifier.identifier = 'doi:10.25338/B8JG7X'
        self.identifier.target = 'http://example.com'
        self.identifier.defaultTarget = 'http://default.com'
        self.identifier.isDatacite = False
        self.identifier.isPublic = True
        self.identifier.exported = True
        self.identifier.isTest = False
        self.identifier.owner = Mock()
        self.identifier.owner.username = 'testuser'
        self.identifier.ownergroup = Mock()
        self.identifier.ownergroup.groupname = 'testgroup'
        self.identifier.metadata = {}

        # Create a mock KernelMetadata object
        self.km = Mock()
        self.km.creator = 'Test Creator'
        self.km.title = 'Test Title'
        self.km.publisher = 'Test Publisher'
        self.km.date = '2022-01-01'
        self.km.type = 'Test Type'
        self.km.validatedDate = '2022'
        self.km.validatedType = 'Dataset/dataset'

        self.identifier.kernelMetadata = self.km

        # Create the OpenSearch object to test
        self.open_search = OpenSearch(self.identifier)

    def test_searchable_target(self):
        self.assertEqual(self.open_search.searchable_target, 'moc.elpmaxe//:ptth')

    def test_resource_creator(self):
        self.assertEqual(self.open_search.resource_creator, 'Test Creator')

    def test_resource_creators(self):
        self.assertEqual(self.open_search.resource_creators, ['Test Creator'])

    def test_resource_title(self):
        self.assertEqual(self.open_search.resource_title, 'Test Title')

    def test_resource_publisher(self):
        self.assertEqual(self.open_search.resource_publisher, 'Test Publisher')

    def test_resource_publication_date(self):
        self.assertEqual(self.open_search.resource_publication_date, '2022-01-01')

    def test_searchable_publication_year(self):
        self.assertEqual(self.open_search.searchable_publication_year, 2022)

    def test_resource_type(self):
        self.assertEqual(self.open_search.resource_type, 'Test Type')

    def test_searchable_resource_type(self):
        self.assertEqual(self.open_search.searchable_resource_type, 'D')

    def test_word_bucket(self):
        expected_word_bucket = 'doi:10.25338/B8JG7X ; testuser ; testgroup ; http://example.com'
        self.assertEqual(self.open_search.word_bucket, expected_word_bucket)

    def test_resource_creator_prefix(self):
        self.assertEqual(self.open_search.resource_creator_prefix, 'Test Creator')

    def test_resource_title_prefix(self):
        self.assertEqual(self.open_search.resource_title_prefix, 'Test Title')

    def test_resource_publisher_prefix(self):
        self.assertEqual(self.open_search.resource_publisher_prefix, 'Test Publisher')

    def test_has_metadata(self):
        self.assertTrue(self.open_search.has_metadata)

    def test_public_search_visible(self):
        self.assertTrue(self.open_search.public_search_visible)

    def test_oai_visible(self):
        self.assertTrue(self.open_search.oai_visible)

    @responses.activate
    def test_index_exists(self):
        url = 'http://opensearch.example.com/ezid-test-index'

        # Define the response you want to return
        responses.add(responses.HEAD, url, status=200)

        result = self.open_search.index_exists()

        self.assertTrue(result)

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, url)

    def test_index_document(self):
        # This method makes a request to an external service, so it's a bit more difficult to test.
        # You might want to use a library like responses to stub out the request.
        pass

    # Add more test methods here...

if __name__ == '__main__':
    unittest.main()