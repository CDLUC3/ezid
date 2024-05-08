import pdb
from opensearchpy import OpenSearch
from opensearch_dsl import Search, Q
from django.conf import settings
import urllib
import impl.util
from ezidapp.models.identifier import Identifier
import ezidapp.models.identifier

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
    """Execute a search database query, returning an evaluated QuerySet

    'user' is the requestor, and should be an authenticated User
    object or AnonymousUser. 'from_' and 'to' are range bounds, and
    must be supplied. 'constraints', 'orderBy', 'selectRelated', and
    'defer' are as in formulateQuery above.
    """

    filters = simpler_formulate_query(constraints, orderBy=orderBy, selectRelated=selectRelated, defer=defer)

    if 'keywords' in constraints:
        # Define the multi_match query
        multi_match_query = Q("multi_match", query=constraints['keywords'], fields=["*"])
        # Combine the multi_match query and the filters using a bool query
        bool_query = Q('bool', must=multi_match_query, filter=filters)
    else:
        bool_query = Q('bool', filter=filters)

    # Use the bool query in the search
    s = Search(using=client, index=settings.OPENSEARCH_INDEX)
    s = s.query(bool_query)

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

    # this is probably a function that will need to go or at least be modified to only give count estimates since
    # getting all possible results just to get a count is wasteful and most large search systems do not give a full
    # count of results or exact number of pages.  They simply give results up to a point and then allow going to the
    # next page or set of pages without commiting to a full count.
    print('hello count world')
    return 10


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


# trying to make the formulate query less long and complicated
def simpler_formulate_query(
    constraints, orderBy=None, selectRelated=defaultSelectRelated, defer=defaultDefer
):
    translate_columns = {
        "exported": "exported",
        "isTest": "is_test",
        "hasMetadata": "has_metadata",
        "publicSearchVisible": "public_search_visible",
        # "linkIsBroken": "linkIsBroken",  TODO: this is not part of the OpenSearch hit
        # "hasIssues": "hasIssues", TODO: this is not part of the OpenSearch hit,
        "createTime": "create_time",
        "updateTime": "update_time",
        "resourceCreator": "resource.creators",
        "resourceTitle": "resource.title",
        "resourcePublisher": "resource.publisher",
        "keywords": "word_bucket",
    }

    filters = []
    scopeRequirementMet = False
    for column, value in list(constraints.items()):
        if column in [
            "exported",
            "isTest",
            "hasMetadata",
            "publicSearchVisible",
            # "linkIsBroken",
            # "hasIssues",
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

            # filter_dict = {"prefix": {"_id": v}}
            filter_dict = {"term": {"_id": v}}
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
                    filter_dict = {"range": {translate_columns[column]: {"gt": value[0]}}}
                filters.append(Q(filter_dict))
            else:
                if value[1] is not None:
                    filter_dict = {"range": {translate_columns[column]: {"lt": value[1]}}}
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
            filter_dict = {"term": {translate_columns[column]: value}}
            filters.append(Q(filter_dict))

        elif column == "resourcePublicationYear":
            if value[0] is not None:
                if value[1] is not None:
                    if value[0] == value[1]:
                        filter_dict = {"term": {"searchable_publication_year": value[0]}}
                        filters.append(Q(searchablePublicationYear=value[0]))
                    else:
                        filters.append(django.db.models.Q(searchablePublicationYear__range=value))
                else:
                    filters.append(django.db.models.Q(searchablePublicationYear__gte=value[0]))
            else:
                if value[1] is not None:
                    filters.append(django.db.models.Q(searchablePublicationYear__lte=value[1]))

    return filters


# note: holy crap this function is out of control at like 300 lines.  TODO: Code smell
# noinspection PyDefaultArgument,PyDefaultArgument
def formulate_query(
    query, constraints, orderBy=None, selectRelated=defaultSelectRelated, defer=defaultDefer
):
    """
    Formulates a search database query and returns an unevaluated
    QuerySet that can then be evaluated, indexed, etc. 'constraints'
    should be a dictionary mapping search columns to constraint values.
    The accepted search columns (most of which correspond to fields in
    the Identifier and Identifier models) and associated
    constraint Python types and descriptions are listed in the table
    below. The 'R' flag indicates if multiple constraints may be placed
    against the column; if yes, multiple constraint values should be
    expressed as a list, and the constraints will be OR'd together. The
    'O' flag indicates if the column may be used for ordering results.
    Descending ordering is achieved, Django-style, by prefixing the
    column name with a minus sign.

    =========================================================================
                        |   |   | constraint |
    search column       | R | O | type       | constraint value
    --------------------+---+---+------------+-------------------------------
    identifier          |   | Y | str        | qualified identifier, e.g.,
                        |   |   |            | "ark:/12345/foo", not
                        |   |   |            | necessarily normalized; if not
                        |   |   |            | qualified, the scheme will be
                        |   |   |            | guessed
    identifierType      | Y | Y | str        | identifier scheme, e.g.,
                        |   |   |            | "ARK", upper- or lowercase
    owner               | Y | Y | str        | username
    ownergroup          | Y | Y | str        | groupname
    createTime          |   | Y | (int, int) | time range as pair of Unix
                        |   |   |            | timestamps; bounds are
                        |   |   |            | inclusive; either/both bounds
                        |   |   |            | may be None
    updateTime          |   | Y | (int, int) | ditto
    status              | Y | Y | str        | status display value, e.g.,
                        |   |   |            | "public"
    exported            |   | Y | bool       |
    crossref            |   |   | bool       | True if the identifier is
                        |   |   |            | registered with Crossref
    crossrefStatus      | Y |   | str        | Crossref status code
    target              |   |   | str        | URL
    profile             | Y | Y | str        | profile label, e.g., "erc"
    isTest              |   | Y | bool       |
    resourceCreator     |   | Y | str        | limited fulltext-style boolean
                        |   |   |            | expression, e.g.,
                        |   |   |            | '"green eggs" OR ham'
    resourceTitle       |   | Y | str        | ditto
    resourcePublisher   |   | Y | str        | ditto
    keywords            |   |   | str        | ditto
    resourcePublica-    |   | Y | (int, int) | time range as pair of years;
      tionYear          |   |   |            | bounds are inclusive; either/
                        |   |   |            | both bounds may be None
    resourceType        | Y | Y | str        | general resource type, e.g.,
                        |   |   |            | "Image"
    hasMetadata         |   | Y | bool       |
    publicSearchVisible |   | Y | bool       |
    linkIsBroken        |   | Y | bool       |
    hasIssues           |   | Y | bool       |
    -------------------------------------------------------------------------

    'constraints' must include one or more of: an owner constraint, an
    ownergroup constraint, or a publicSearchVisible=True constraint; if
    not, an assertion error is raised. Otherwise, this function is
    forgiving, and will produce a QuerySet even if constraint values are
    nonsensical.
    """
    filters = []
    scopeRequirementMet = False
    for column, value in list(constraints.items()):
        if column in [
            "exported",
            "isTest",
            "hasMetadata",
            "publicSearchVisible",
            "linkIsBroken",
            "hasIssues",
        ]:
            filters.append(django.db.models.Q(**{column: value}))
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
            filters.append(django.db.models.Q(identifier__istartswith=v))
        elif column == "identifierType":
            if isinstance(value, str):
                value = [value]
            filters.append(
                functools.reduce(
                    operator.or_,
                    [django.db.models.Q(identifier__startswith=(v.lower() + ":")) for v in value],
                )
            )
        elif column == "owner":
            if isinstance(value, str):
                value = [value]
            filters.append(
                functools.reduce(
                    operator.or_, [django.db.models.Q(owner__username=v) for v in value]
                )
            )
            scopeRequirementMet = True
        elif column == "ownergroup":
            if isinstance(value, str):
                value = [value]
            filters.append(
                functools.reduce(
                    operator.or_,
                    [django.db.models.Q(ownergroup__groupname=v) for v in value],
                )
            )
            scopeRequirementMet = True
        elif column in ["createTime", "updateTime"]:
            if value[0] is not None:
                if value[1] is not None:
                    filters.append(django.db.models.Q(**{(column + "__range"): value}))
                else:
                    filters.append(django.db.models.Q(**{(column + "__gte"): value[0]}))
            else:
                if value[1] is not None:
                    filters.append(django.db.models.Q(**{(column + "__lte"): value[1]}))
        elif column == "status":

            filters.append(
                functools.reduce(
                    operator.or_,
                    [
                        django.db.models.Q(
                            status=ezidapp.models.identifier.Identifier.statusDisplayToCode.get(
                                v, v
                            )
                        )
                        for v in value
                    ],
                )
            )
        elif column == "crossref":
            if value:
                filters.append(~django.db.models.Q(crossrefStatus=""))
            else:
                filters.append(django.db.models.Q(crossrefStatus=""))
        elif column == "crossrefStatus":
            if isinstance(value, str):
                value = [value]
            filters.append(
                functools.reduce(
                    operator.or_, [django.db.models.Q(crossrefStatus=v) for v in value]
                )
            )
        elif column == "target":
            # Unfortunately we don't store URLs in any kind of normalized
            # form, so we have no real means to take URL equivalence into
            # account. The one thing we give flexibility on in matching is
            # the presence or absence of a trailing slash (well, that and
            # case-insensitivity.)
            values = [value]
            u = urllib.parse.urlparse(value)
            if u.params == "" and u.query == "" and u.fragment == "":
                # Make sure all post-path syntax is removed.
                value = u.geturl()
                if value.endswith("/"):
                    values.append(value[:-1])
                else:
                    values.append(value + "/")
            qlist = []
            for v in values:
                q = django.db.models.Q(
                    searchableTarget=v[::-1][: ezidapp.models.identifier.MAX_SEARCHABLE_TARGET_LENGTH]
                )
                # noinspection PyTypeChecker
                if len(v) > ezidapp.models.identifier.MAX_SEARCHABLE_TARGET_LENGTH:
                    q &= django.db.models.Q(target=v)
                qlist.append(q)
            filters.append(functools.reduce(operator.or_, qlist))
        elif column == "profile":
            if isinstance(value, str):
                value = [value]
            filters.append(
                functools.reduce(
                    operator.or_, [django.db.models.Q(profile__label=v) for v in value]
                )
            )
        elif column in _fulltextFields:
            filters.append(
                django.db.models.Q(**{(column + "__search"): _processFulltextConstraint(value)})
            )
        elif column == "resourcePublicationYear":
            if value[0] is not None:
                if value[1] is not None:
                    if value[0] == value[1]:
                        filters.append(django.db.models.Q(searchablePublicationYear=value[0]))
                    else:
                        filters.append(django.db.models.Q(searchablePublicationYear__range=value))
                else:
                    filters.append(django.db.models.Q(searchablePublicationYear__gte=value[0]))
            else:
                if value[1] is not None:
                    filters.append(django.db.models.Q(searchablePublicationYear__lte=value[1]))
        elif column == "resourceType":
            if isinstance(value, str):
                value = [value]
            filters.append(
                functools.reduce(
                    operator.or_,
                    [
                        django.db.models.Q(
                            searchableResourceType=ezidapp.models.validation.resourceTypes.get(v, v)
                        )
                        for v in value
                    ],
                )
            )
        else:
            assert False, "unrecognized column"
    assert scopeRequirementMet, "query scope requirement not met"

    qs = ezidapp.models.identifier.SearchIdentifier.objects.filter(*filters)

    if len(selectRelated) > 0:
        qs = qs.select_related(*selectRelated)
    if len(defer) > 0:
        qs = qs.defer(*defer)
    if orderBy is not None:
        prefix = ""
        if orderBy.startswith("-"):
            prefix = "-"
            orderBy = orderBy[1:]
        if orderBy in [
            "identifier",
            "createTime",
            "updateTime",
            "status",
            "exported",
            "isTest",
            "hasMetadata",
            "publicSearchVisible",
            "linkIsBroken",
            "hasIssues",
        ]:
            pass
        elif orderBy == "identifierType":
            orderBy = "identifier"
        elif orderBy == "owner":
            orderBy = "owner__username"
        elif orderBy == "ownergroup":
            orderBy = "ownergroup__groupname"
        elif orderBy == "profile":
            orderBy = "profile__label"
        elif orderBy == "resourceCreator":
            orderBy = "resourceCreatorPrefix"
        elif orderBy == "resourceTitle":
            orderBy = "resourceTitlePrefix"
        elif orderBy == "resourcePublisher":
            orderBy = "resourcePublisherPrefix"
        elif orderBy == "resourcePublicationYear":
            orderBy = "searchablePublicationYear"
        elif orderBy == "resourceType":
            orderBy = "searchableResourceType"
        else:
            assert False, "column does not support ordering"
        qs = qs.order_by(prefix + orderBy)
    return qs