import pdb
from opensearchpy import OpenSearch
from opensearch_dsl import Search, Q
from django.conf import settings
import urllib

settings.OPENSEARCH_BASE

parsed_url = urllib.parse.urlparse(settings.OPENSEARCH_BASE)
client = OpenSearch(
    hosts = [{'host': parsed_url.hostname, 'port': parsed_url.port}],
    http_compress = True, # enables gzip compression for request bodies
    http_auth = (settings.OPENSEARCH_USER, settings.OPENSEARCH_PASSWORD),
    use_ssl = True,
    verify_certs = True,
    ssl_assert_hostname = False,
    ssl_show_warn = False
)


defaultSelectRelated = ["owner", "ownergroup"]
defaultDefer = [
    "cm",
    "keywords",
    "target",
    "searchableTarget",
    "resourceCreatorPrefix",
    "resourceTitlePrefix",
    "resourcePublisherPrefix",
]


def executeSearch(
    user,
    constraints,
    from_,
    to,
    orderBy=None,
    selectRelated=defaultSelectRelated,
    defer=defaultDefer,
):
    """Execute a search database query, returning an evaluated QuerySet

    'user' is the requestor, and should be an authenticated User
    object or AnonymousUser. 'from_' and 'to' are range bounds, and
    must be supplied. 'constraints', 'orderBy', 'selectRelated', and
    'defer' are as in formulateQuery above.
    """

    s = Search(using=client, index=settings.OPENSEARCH_INDEX)
    # Define the query
    query = Q("multi_match", query=constraints['keywords'], fields=["*"])
    s = s.query(query)
    response = s.execute()

    pdb.set_trace()
    print('hello search world')

# noinspection PyDefaultArgument,PyDefaultArgument
def executeSearchCountOnly(
      user, constraints, selectRelated=defaultSelectRelated, defer=defaultDefer
):
    """Execute a search database query, returning just the number of results

    'user' is the requestor, and should be an authenticated User
    object or AnonymousUser. 'constraints', 'selectRelated', and
    'defer' are as in formulateQuery above.
    """

    # this is probably a function that will need to go or at least be modified to only give count estimates since
    # getting all possible results just to get a count is wasteful and most large search systems do not give a full
    # count of results or exact number of pages.  They simply give results up to a point and then allow going to the
    # next page or set of pages without commiting to a full count.
    print('hello count world')
    return 10