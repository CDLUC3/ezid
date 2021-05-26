# =============================================================================
#
# EZID :: search_util.py
#
# Search-related utilities.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import functools
import operator
import re
import threading
import time
import urllib.parse
import uuid

import django.conf
import django.db
import django.db.models
import django.db.utils

# import ezidapp.models.realm
import ezidapp.models.identifier
import ezidapp.models.realm
import ezidapp.models.validation
import impl.log
import impl.util

_lock = threading.Lock()


# noinspection PyProtectedMember
_maxTargetLength = ezidapp.models.identifier.SearchIdentifier._meta.get_field(
    "searchableTarget"
).max_length

_stopwords = None
_minimumWordLength = None
django.conf.settings.DATABASES["search"][
    "fulltextSearchSupported"
] = django.conf.settings.DATABASES["search"]["fulltextSearchSupported"]
if django.conf.settings.DATABASES["search"]["fulltextSearchSupported"]:
    _stopwords = (
        django.conf.settings.SEARCH_STOPWORDS
        + " "
        + django.conf.settings.SEARCH_EXTRA_STOPWORDS
    ).split()
    _minimumWordLength = int(django.conf.settings.SEARCH_MINIMUM_WORD_LENGTH)

_numActiveSearches = 0


class AbortException(Exception):
    pass


def withAutoReconnect(functionName, function, continuationCheck=None):
    """Calls 'function' and returns the result.

    If an operational database error is encountered (e.g., a lost
    connection), the call is repeated until it succeeds.
    'continuationCheck', if not None, should be another function that
    signals when the attempts should cease by raising an exception or
    returning False.  If 'continuationCheck' returns False, this
    function raises AbortException (defined in this module).
    'functionName' is the name of 'function' for logging purposes.
    """
    firstError = True
    while True:
        try:
            return function()
        except django.db.OperationalError as e:
            # We're silent about the first error because it might simply be
            # due to the database connection having timed out.
            if not firstError:
                impl.log.otherError("search_util.withAutoReconnect/" + functionName, e)
                # noinspection PyTypeChecker
                time.sleep(int(django.conf.settings.DATABASES_RECONNECT_DELAY))
            if continuationCheck is not None and not continuationCheck():
                raise AbortException()
            # In some cases a lost connection causes the thread's database
            # connection object to be permanently screwed up.  The following
            # call solves the problem.  (Note that Django's database
            # connection objects are indexed generically, but are stored
            # thread-local.)
            django.db.connections["search"].close()
            firstError = False


def ping():
    """Tests the search database, returning "up" or "down"."""
    try:
        _n = ezidapp.models.realm.SearchRealm.objects.count()
    except Exception:
        return "down"
    else:
        return "up"


_fulltextFields = ["resourceCreator", "resourceTitle", "resourcePublisher", "keywords"]


def _processFulltextConstraint(constraint):
    # The primary purposes of this function are 1) to remove characters
    # that might be interpreted by MySQL as operators and 2) to change
    # the default semantics of MySQL's freetext search from OR to AND.
    # The latter is accomplished by making every search term required,
    # so that a constraint "foo bar" is transformed into "+foo +bar".
    # Quoted phrases are treated like atomic terms and are left as is.
    # Additionally, this function implements an explicit OR operator.
    # An "OR" placed between two terms has the effect of making those
    # terms optional.  Thus, "foo bar OR baz" becomes "+foo bar baz".
    # Finally, stopwords are removed.
    #
    # Step 1: Parse the constraint into words and quoted phrases.  MySQL
    # interprets some characters as operators, and will return an error
    # if a query is malformed according to its less-than-well-defined
    # rules.  For safety we remove all operators that are outside double
    # quotes (i.e., quotes are the only MySQL operator we retain).
    inQuote = False
    inWord = False
    words = []
    for c in constraint:
        if c == '"':
            if inQuote:
                words[-1].append(c)
                inQuote = False
            else:
                words.append([])
                words[-1].append(c)
                inQuote = True
                inWord = False
        elif c.isalnum():
            if inQuote or inWord:
                words[-1].append(c)
            else:
                words.append([])
                words[-1].append(c)
                inWord = True
        else:
            if inQuote:
                words[-1].append(c)
            else:
                inWord = False
    if inQuote:
        words[-1].append('"')
    # Step 2.  OR processing.  All OR terms are ultimately discarded.
    words = [[True, "".join(w)] for w in words]
    i = 0
    while i < len(words):
        if words[i][1].upper() == "OR":
            # noinspection PyChainedComparisons
            if i > 0 and i < len(words) - 1:
                words[i - 1][0] = False
                words[i + 1][0] = False
            del words[i]
        else:
            i += 1
    # Step 3.  Remove all stopwords.  We can't leave MySQL's default
    # stopwords in because a plus sign in front of a stopword will cause
    # zero results to be returned.  Also, we need to remove our own
    # stopwords anyway.
    i = 0
    while i < len(words):
        # noinspection PyTypeChecker
        if not words[i][1].startswith('"') and (
            len(words[i][1]) < _minimumWordLength or (words[i][1]).lower() in _stopwords
        ):
            del words[i]
        else:
            i += 1
    if len(words) > 0:
        return " ".join(f"{'+' if w[0] else ''}{w[1]}" for w in words)
    else:
        # If a constraint has no search terms (e.g., consists of all
        # stopwords), MySQL returns zero results.  To mimic this behavior
        # we return an arbitrary constraint having the same behavior.
        return "+x"


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


# noinspection PyDefaultArgument,PyDefaultArgument
def formulateQuery(
    constraints, orderBy=None, selectRelated=defaultSelectRelated, defer=defaultDefer
):
    """
    Formulates a search database query and returns an unevaluated
    QuerySet that can then be evaluated, indexed, etc.  'constraints'
    should be a dictionary mapping search columns to constraint values.
    The accepted search columns (most of which correspond to fields in
    the Identifier and SearchIdentifier models) and associated
    constraint Python types and descriptions are listed in the table
    below.  The 'R' flag indicates if multiple constraints may be placed
    against the column; if yes, multiple constraint values should be
    expressed as a list, and the constraints will be OR'd together.  The
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
    not, an assertion error is raised.  Otherwise, this function is
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
            if column == "publicSearchVisible" and value == True:
                scopeRequirementMet = True
        elif column == "identifier":
            v = impl.util.validateIdentifier(value)
            if v is None:
                if re.match("\d{5}/", value):
                    v = impl.util.validateArk(value)
                    if v is not None:
                        v = "ark:/" + v
                elif re.match("10\.[1-9]\d{3,4}/", value):
                    v = impl.util.validateDoi(value)
                    if v is not None:
                        v = "doi:" + v
                if v is None:
                    v = value
            filters.append(django.db.models.Q(identifier__startswith=v))
        elif column == "identifierType":
            if isinstance(value, str):
                value = [value]
            filters.append(
                functools.reduce(
                    operator.or_,
                    [
                        django.db.models.Q(identifier__startswith=(v.lower() + ":"))
                        for v in value
                    ],
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
            if isinstance(value, str):
                value = [value]
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
            # account.  The one thing we give flexibility on in matching is
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
                q = django.db.models.Q(searchableTarget=v[::-1][:_maxTargetLength])
                # noinspection PyTypeChecker
                if len(v) > _maxTargetLength:
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
            if django.conf.settings.DATABASES["search"]["fulltextSearchSupported"]:
                filters.append(
                    django.db.models.Q(
                        **{(column + "__search"): _processFulltextConstraint(value)}
                    )
                )
            else:
                value = value.split()
                if len(value) > 0:
                    filters.append(
                        functools.reduce(
                            operator.and_,
                            [
                                django.db.models.Q(**{(column + "__icontains"): v})
                                for v in value
                            ],
                        )
                    )
        elif column == "resourcePublicationYear":
            if value[0] is not None:
                if value[1] is not None:
                    if value[0] == value[1]:
                        filters.append(
                            django.db.models.Q(searchablePublicationYear=value[0])
                        )
                    else:
                        filters.append(
                            django.db.models.Q(searchablePublicationYear__range=value)
                        )
                else:
                    filters.append(
                        django.db.models.Q(searchablePublicationYear__gte=value[0])
                    )
            else:
                if value[1] is not None:
                    filters.append(
                        django.db.models.Q(searchablePublicationYear__lte=value[1])
                    )
        elif column == "resourceType":
            if isinstance(value, str):
                value = [value]
            filters.append(
                functools.reduce(
                    operator.or_,
                    [
                        django.db.models.Q(
                            searchableResourceType=ezidapp.models.validation.resourceTypes.get(
                                v, v
                            )
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


def _modifyActiveCount(delta):
    global _numActiveSearches
    _lock.acquire()
    try:
        _numActiveSearches += delta
    finally:
        _lock.release()


def numActiveSearches():
    """Returns the number of active searches."""
    _lock.acquire()
    try:
        return _numActiveSearches
    finally:
        _lock.release()


def _isMysqlFulltextError(exception):
    return isinstance(exception, django.db.utils.InternalError) and exception.args == (
        188,
        "FTS query exceeds result cache limit",
    )


# noinspection PyDefaultArgument,PyDefaultArgument
def executeSearchCountOnly(
    user, constraints, selectRelated=defaultSelectRelated, defer=defaultDefer
):
    """Executes a search database query, returning just the number of results.

    'user' is the requestor, and should be an authenticated StoreUser
    object or AnonymousUser.  'constraints', 'selectRelated', and
    'defer' are as in formulateQuery above.
    """
    tid = uuid.uuid1()
    try:
        _modifyActiveCount(1)
        qs = formulateQuery(constraints, selectRelated=selectRelated, defer=defer)
        # noinspection PyTypeChecker
        impl.log.begin(
            tid,
            "search/count",
            "-",
            user.username,
            user.pid,
            user.group.groupname,
            user.group.pid,
            *functools.reduce(
                operator.__concat__, [[k, str(v)] for k, v in list(constraints.items())]
            ),
        )
        c = qs.count()
    except Exception as e:
        # MySQL's FULLTEXT engine chokes on a too-frequently-occurring
        # word (call it a "bad" word) that is not on its own stopword
        # list.  We weed out bad words using our own stopword list, but
        # not if they're quoted, and unfortunately MySQL chokes on bad
        # words quoted or not.  Furthermore, we are unable to add to
        # MySQL's stopword list.  If MySQL chokes, we retry the query
        # without any quotes in the hopes that any quoted bad words will
        # be removed by our own processing.
        if _isMysqlFulltextError(e) and any(
            '"' in constraints.get(f, "") for f in _fulltextFields
        ):
            constraints2 = constraints.copy()
            for f in _fulltextFields:
                if f in constraints2:
                    constraints2[f] = constraints2[f].replace('"', " ")
            impl.log.success(tid, "-1")
            return executeSearchCountOnly(user, constraints2, selectRelated, defer)
        else:
            impl.log.error(tid, e)
            raise
    else:
        impl.log.success(tid, str(c))
        return c
    finally:
        _modifyActiveCount(-1)


# noinspection PyDefaultArgument,PyDefaultArgument
def executeSearch(
    user,
    constraints,
    from_,
    to,
    orderBy=None,
    selectRelated=defaultSelectRelated,
    defer=defaultDefer,
):
    """Executes a search database query, returning an evaluated QuerySet.

    'user' is the requestor, and should be an authenticated StoreUser
    object or AnonymousUser.  'from_' and 'to' are range bounds, and
    must be supplied.  'constraints', 'orderBy', 'selectRelated', and
    'defer' are as in formulateQuery above.
    """
    tid = uuid.uuid1()
    try:
        _modifyActiveCount(1)
        qs = formulateQuery(
            constraints, orderBy=orderBy, selectRelated=selectRelated, defer=defer
        )
        # noinspection PyTypeChecker
        impl.log.begin(
            tid,
            "search/results",
            "-",
            user.username,
            user.pid,
            user.group.groupname,
            user.group.pid,
            str(orderBy),
            str(from_),
            str(to),
            *functools.reduce(
                operator.__concat__, [[k, str(v)] for k, v in list(constraints.items())]
            ),
        )
        qs = qs[from_:to]
        c = len(qs)
    except Exception as e:
        # MySQL's FULLTEXT engine chokes on a too-frequently-occurring
        # word (call it a "bad" word) that is not on its own stopword
        # list.  We weed out bad words using our own stopword list, but
        # not if they're quoted, and unfortunately MySQL chokes on bad
        # words quoted or not.  Furthermore, we are unable to add to
        # MySQL's stopword list.  If MySQL chokes, we retry the query
        # without any quotes in the hopes that any quoted bad words will
        # be removed by our own processing.
        if _isMysqlFulltextError(e) and any(
            '"' in constraints.get(f, "") for f in _fulltextFields
        ):
            constraints2 = constraints.copy()
            for f in _fulltextFields:
                if f in constraints2:
                    constraints2[f] = constraints2[f].replace('"', " ")
            impl.log.success(tid, "-1")
            return executeSearch(
                user, constraints2, from_, to, orderBy, selectRelated, defer
            )
        else:
            impl.log.error(tid, e)
            raise
    else:
        impl.log.success(tid, str(c))
        return qs
    finally:
        _modifyActiveCount(-1)
