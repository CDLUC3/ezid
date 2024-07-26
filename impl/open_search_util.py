import urllib

from opensearchpy import OpenSearch
from opensearch_dsl import Search, Q
from django.conf import settings
import impl.util
from ezidapp.models.identifier import Identifier
import ezidapp.models.identifier
import re
from impl.open_search_doc import OpenSearchDoc

settings.OPENSEARCH_BASE

client = OpenSearchDoc.CLIENT

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

# This utility is a conversion of the older search_util.py to use OpenSearch instead of the database.

# I needed to create a few helper functions and inline them here for some functions which existed in other
# modules in the original codebase


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

    filters = formulate_query(constraints, orderBy=orderBy, selectRelated=selectRelated, defer=defer)

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

    # limit to 2 results since the s.count returns the number of hits (estimated?) without loading all
    # the records and even items with hundreds of thousands of results product a count quickly.
    # Without limiting this first and doing a count, it times out with a large number of results, which seems
    # kind of wrong since it should be able to count without loading all the records, but there is a huge
    # performance increase by doing it this way and prevents large queries like searching for the word "California"
    # from timing out and giving a 504 error in the web application.
    s = s[0:1]

    return s.count()


def issue_reasons(hit):
    # Returns a list of the identifier's issues.
    reasons = []
    if not hit['has_metadata']:
        reasons.append("missing metadata")
    if hit['link_is_broken']:
        reasons.append("broken link")
    if is_crossref_bad(hit):
        reasons.append(
            "Crossref registration "
            + ("warning" if hit['crossref_status'] == Identifier.CR_WARNING else "failure")
        )
    return reasons


# a similar method exists in the database model for identifier, but this recreates the same logic based on the
# OpenSearch hit
def is_crossref_bad(hit):
    return hit['crossref_status'] in [Identifier.CR_WARNING, Identifier.CR_FAILURE]


# a similar method exists in the database model for identifier, but this recreates the same logic based on the
# OpenSearch hit
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


# This is a long method which mirrors the original search_util.py's formulateQuery method which was also long.
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

            filter_dict = {"prefix": {"searchable_id": v}}
            # filter_dict = {"term": {"_id": v}}
            filters.append(Q(filter_dict))

        elif column == "identifierType":
            if isinstance(value, str):
                value = [value]
            filter_dict = {"terms": {"identifier_type.keyword": value}}
            filters.append(Q(filter_dict))

        elif column == "owner":
            if isinstance(value, str):
                value = [value]
            filter_dict = {"terms": {"owner.username.keyword": value}}
            filters.append(Q(filter_dict))
            scopeRequirementMet = True

        elif column == "ownergroup":
            if isinstance(value, str):
                value = [value]
            filter_dict = {"terms": {"ownergroup.name.keyword": value}}
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
            filter_dict = {"terms": {"status.keyword": stat_vals}}
            filters.append(Q(filter_dict))

        elif column == "crossref":
            if value:
                filter_dict = {"term": {"crossref_status.keyword": ""}}
                filters.append(Q('bool',
                                    must=Q('exists', field='crossref_status.keyword'),
                                    must_not=Q(filter_dict)))
            else:
                filters.append(Q({"term": {"crossref_status.keyword": ""}}))

        elif column == "crossrefStatus":
            if isinstance(value, str):
                value = [value]
            filter_dict = {"terms": {"crossref_status.keyword": value}}
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

            # We don't need to check for MAX_SEARCHABLE_TARGET_LENGTH in OpenSearch, but refer to search_util
            # for how it was done with database if we need to re-add this limitation. OpenSearch limits automatically
            # as set up in the schema.
            filter_dict = {"terms": {"target.keyword": values}}
            filters.append(Q(filter_dict))

        elif column == "profile":
            if isinstance(value, str):
                value = [value]
            filter_dict = {"terms": {"profile.label.keyword": value}}
            filters.append(Q(filter_dict))

        elif column in _fulltextFields:
            must_words, should_words = words_to_must_and_should(value)

            must_queries = [Q("match", **{translate_columns[column]: word}) for word in must_words]
            should_queries = [Q("match", **{translate_columns[column]: word}) for word in should_words]

            if must_queries and not should_queries:
                bool_query = Q('bool', must=must_queries)
            elif should_queries and not must_queries:
                bool_query = Q('bool', should=should_queries, minimum_should_match=1)
            else:
                bool_query = Q('bool', must=must_queries, should=should_queries, minimum_should_match=1)

            filters.append(bool_query)

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

            searchable_vals = [ezidapp.models.validation.resourceTypes.get(v, v) for v in value]
            filter_dict = {"terms": {"resource.searchable_type.keyword": searchable_vals}}
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


def words_to_must_and_should(the_string):
    words = the_string.split()
    must_words = []
    should_words = []
    last_word = ''
    for word in words:
        if last_word == "OR":
            should_words.append(word)  # this attaches the current word, following an OR, to the should_words list
        elif word == "AND":
            continue  # ignore AND since it's the default. We don't need to search on it
        elif word == "OR" and last_word != '':
            # move the previous word from the must_words list to the should_words list
            should_words.append(must_words.pop())
        else:
            must_words.append(word)
        last_word = word

    return must_words, should_words
