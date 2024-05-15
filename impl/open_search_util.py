import pdb
from opensearchpy import OpenSearch
from opensearch_dsl import Search, Q
from django.conf import settings
import urllib
import impl.util
from ezidapp.models.identifier import Identifier
import ezidapp.models.identifier
import re

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

_fulltextFields = ["resourceCreator", "resourceTitle", "resourcePublisher", "keywords"]


def executeSearch(
    user,
    constraints,
    from_,
    to,
    orderBy=None,
    selectRelated=defaultSelectRelated,
    defer=defaultDefer
):
    """Execute a search opensearch query, returning an evaluated QuerySet

    'user' is the requestor, and should be an authenticated User
    object or AnonymousUser. 'from_' and 'to' are range bounds, and
    must be supplied. 'constraints', 'orderBy', 'selectRelated', and
    'defer' are as in formulateQuery above.
    """

    # TODO: is it a bug that in the original code the only place user is used is in logging?
    # I would'vee thought results would be limited by user permission somehow, but I'm not sure they are.

    filters = formulate_query(constraints, orderBy=orderBy, selectRelated=selectRelated, defer=defer)

    # if 'keywords' in constraints:
    #     # Define the multi_match query
    #     multi_match_query = Q("multi_match", query=constraints['keywords'], fields=["*"])
    #     # Combine the multi_match query and the filters using a bool query
    #     bool_query = Q('bool', must=multi_match_query, filter=filters)
    # else:

    bool_query = Q('bool', filter=filters)

    # Use the bool query in the search
    s = Search(using=client, index=settings.OPENSEARCH_INDEX)
    s = s.query(bool_query)

    # call the ordering function
    if orderBy is not None:
        order_dict = formulate_order_by(orderBy)
        if order_dict is not None:
            s = s.sort(order_dict)

    # return only the correct page of records
    s = s[from_:to]

    # Execute the search
    response = s.execute()

    # response.hits.total.value is number of hits
    # response.hits.hits is the list of hits

    return response

# noinspection PyDefaultArgument,PyDefaultArgument
def executeSearchCountOnly(
      user, constraints, selectRelated=defaultSelectRelated, defer=defaultDefer
):
    """Execute a search OpenSearch query, returning just the number of results

    'user' is the requestor, and should be an authenticated User
    object or AnonymousUser. 'constraints', 'selectRelated', and
    'defer' are as in formulateQuery above.
    """

    filters = formulate_query(constraints, orderBy=None, selectRelated=selectRelated, defer=defer)
    bool_query = Q('bool', filter=filters)

    # Use the bool query in the search
    s = Search(using=client, index=settings.OPENSEARCH_INDEX)
    s = s.query(bool_query)

    return s.count()


def issue_reasons(hit):
    # Returns a list of the identifier's issues.
    reasons = []
    if not hit['has_metadata']:
        reasons.append("missing metadata")
    # the False below, was "linkIsBroken" -- which is not part of the OpenSearch hit and in the Identifier model around
    # line 1110.  Apparently calculated by the link checker and not part of the OpenSearch hit currently.  should it be?
    if False:
        reasons.append("broken link")
    if is_crossref_bad:
        reasons.append(
            "Crossref registration "
            + ("warning" if hit['crossref_status'] == Identifier.CR_WARNING else "failure")
        )
    return reasons


def is_crossref_bad(hit):
    return hit['crossref_status'] in [Identifier.CR_WARNING, Identifier.CR_FAILURE]


def is_crossref_good(hit):
    return hit['crossref_status'] in [
        Identifier.CR_RESERVED,
        Identifier.CR_WORKING,
        Identifier.CR_SUCCESS,
    ]


def friendly_status(hit):
    if hit['status'] == Identifier.PUBLIC:
        return "public"
    elif hit['status'] == Identifier.UNAVAILABLE:
        return "unavailable"
    elif hit['status'] == Identifier.RESERVED:
        return "reserved"
    else:
        return "unknown"


# trying to make the formulate query less long and complicated
def formulate_query(
    constraints, orderBy=None, selectRelated=defaultSelectRelated, defer=defaultDefer
):
    translate_columns = {
        "exported": "exported",
        "isTest": "is_test",
        "hasMetadata": "has_metadata",
        "publicSearchVisible": "public_search_visible",
        "linkIsBroken": "link_is_broken",
        "hasIssues": "has_issues",
        "createTime": "create_time",
        "updateTime": "update_time",
        "resourceCreator": "resource.creators",
        "resourceTitle": "resource.title",
        "resourcePublisher": "resource.publisher",
        "keywords": "word_bucket"
    }

    filters = []
    scopeRequirementMet = False
    for column, value in list(constraints.items()):
        if column in [
            "exported",
            "isTest",
            "hasMetadata",
            "publicSearchVisible",
            "linkIsBroken",
            "hasIssues"
        ]:
            filter_dict = {"term": {translate_columns[column]: value}}
            filters.append(Q(filter_dict))
            if column == "publicSearchVisible" and value is True:
                scopeRequirementMet = True

        elif column == "identifier":
            v = impl.util.validateIdentifier(value)
            if v is None:
                if re.match("\\d{5}/", value):
                    v = impl.util.validateArk(value)
                    if v is not None:
                        v = "ark:/" + v
                elif re.match("10\\.[1-9]\\d{3,4}/", value):
                    v = impl.util.validateDoi(value)
                    if v is not None:
                        v = "doi:" + v
                if v is None:
                    v = value
            # TODO: in order for prefix to work, I have to make sure the identifier is indexed as a keyword with
            # a custom mapping for the identifier field in the OpenSearch index, and it still only works in some
            # circumstances.
            # "If search.allow_expensive_queries is set to false, prefix queries are not run."
            # "It's important to note that prefix queries can be resource-intensive and can lead to performance issues.
            # They are not recommended for large scale text searching. For better performance, consider using an edge
            # n-gram tokenizer at index time or a completion suggester for auto-complete functionality."

            filter_dict = {"prefix": {"searchable_id": v}}
            # filter_dict = {"term": {"_id": v}}
            filters.append(Q(filter_dict))

        elif column == "identifierType":
            if isinstance(value, str):
                value = [value]
            filter_dict = {"terms": {"identifier_type": value}}
            filters.append(Q(filter_dict))

        elif column == "owner":
            if isinstance(value, str):
                value = [value]
            filter_dict = {"terms": {"owner.username": value}}
            filters.append(Q(filter_dict))
            scopeRequirementMet = True

        elif column == "ownergroup":
            if isinstance(value, str):
                value = [value]
            filter_dict = {"terms": {"ownergroup.name": value}}
            filters.append(Q(filter_dict))
            scopeRequirementMet = True

        elif column in ["createTime", "updateTime"]:
            if value[0] is not None:
                if value[1] is not None:
                    filter_dict = {"range": {translate_columns[column]: {"gte": value[0], "lte": value[1]}}}
                else:
                    filter_dict = {"range": {translate_columns[column]: {"gte": value[0]}}}
                filters.append(Q(filter_dict))
            else:
                if value[1] is not None:
                    filter_dict = {"range": {translate_columns[column]: {"lte": value[1]}}}
                    filters.append(Q(filter_dict))

        elif column == "status":
            if isinstance(value, str):
                value = [value]
            stat_vals = [ezidapp.models.identifier.Identifier.statusDisplayToCode.get(v, v) for v in value]
            filter_dict = {"terms": {"status": stat_vals}}
            filters.append(Q(filter_dict))

        elif column == "crossref":
            if value:
                filters.append(Q('bool',
                                    must=Q('exists', field='crossref_status'),
                                    must_not=Q('term', crossref_status='')))
            else:
                filters.append(Q('term', crossref_status=''))

        elif column == "crossrefStatus":
            if isinstance(value, str):
                value = [value]
            filter_dict = {"terms": {"crossref_status": value}}
            filters.append(Q(filter_dict))

        elif column == "target":
            # check for both with and without trailing slash match
            values = [value]
            u = urllib.parse.urlparse(value)
            if u.params == "" and u.query == "" and u.fragment == "":
                # Make sure all post-path syntax is removed.
                value = u.geturl()
                if value.endswith("/"):
                    values.append(value[:-1])
                else:
                    values.append(value + "/")

            # I don't think we need to check for MAX_SEARCHABLE_TARGET_LENGTH in OpenSearch, but refer to search_util
            # for how it was done with database if we need to re-add this limitation.
            filter_dict = {"terms": {"target": value}}
            filters.append(Q(filter_dict))

        elif column == "profile":
            if isinstance(value, str):
                value = [value]
            filter_dict = {"terms": {"profile.label": value}}
            filters.append(Q(filter_dict))

        elif column in _fulltextFields:
            filter_dict = {"match": {translate_columns[column]: value}}
            filters.append(Q(filter_dict))

        elif column == "resourcePublicationYear":
            if value[0] is not None:
                if value[1] is not None:
                    if value[0] == value[1]:
                        filter_dict = {"term": {"searchable_publication_year": value[0]}}
                        filters.append(Q(filter_dict))
                    else:
                        filter_dict = {"range": {"searchable_publication_year": {"gte": value[0], "lte": value[1]}}}
                        filters.append(Q(filter_dict))
                else:
                    filter_dict = {"range": {"searchable_publication_year": {"gte": value[0]}}}
                    filters.append(Q(filter_dict))
            else:
                if value[1] is not None:
                    filter_dict = {"range": {"searchable_publication_year": {"lte": value[1]}}}
                    filters.append(Q(filter_dict))

        elif column == "resourceType":
            if isinstance(value, str):
                value = [value]
            filter_dict = {"terms": {"resource.type": value}}
            filters.append(Q(filter_dict))

        else:
            assert False, "unrecognized column"

    return filters


"""
In OpenSearch, you can order the results by a specific column using the sort method on the Search object. The sort
method takes a dictionary where the keys are the field names and the values are the direction of the sort, either
'asc' for ascending or 'desc' for descending.
"""


def formulate_order_by(order_by):
    if order_by is not None:
        direction = "asc"
        if order_by.startswith("-"):
            direction = "desc"
            order_by = order_by[1:]

        order_map = {
                "identifier": 'searchable_id',
                "createTime": 'create_time',
                "updateTime": 'update_time',
                "status": 'status.keyword',
                "exported": 'exported',
                "isTest": 'is_test',
                "hasMetadata": 'has_metadata',
                "publicSearchVisible": 'public_search_visible',
                "linkIsBroken": 'link_is_broken',
                "hasIssues": 'has_issues',
                "owner": 'owner.username.keyword',
                "identifierType": 'identifier',
                "ownergroup": 'ownergroup.name.keyword',
                "profile": 'profile.label.keyword',
                "resourceCreator": 'resource.creators.keyword',
                "resourceTitle": 'resource.title.keyword',
                "resourcePublisher": 'resource.publisher.keyword',
                "resourcePublicationYear": 'searchable_publication_year',
                "resourceType": 'resource.type.keyword'
        }

        if order_by not in order_map:
            return None

        order_dict = {order_map[order_by]: {'order': direction}}
        return order_dict

