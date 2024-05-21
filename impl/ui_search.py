#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import pdb
import locale
import math
import operator
import re
from datetime import datetime
import urllib.error
import urllib.parse
import urllib.request
import urllib.response

from ezidapp.models.identifier import Identifier

import django.conf
import django.contrib.messages
from django.utils.translation import ugettext as _

import impl.form_objects
import impl.open_search_util
import impl.ui_common
import impl.userauth
import impl.util

locale.setlocale(locale.LC_ALL, '')

# Form fields from search are defined in code/form_objects.py.
# Corresponding fields used for column display include a 'c_' prefix.

#######     LAYOUT PROPERTIES     #########
# if I had realized there were going to be so many properties up front, I probably would
# have created a field layout object with a number of properties instead.

# Column IDs mapped to 1) DB constraints names and 2) UI display
FIELDS_MAPPED = {
    'c_create_time': ['createTime', _("ID Date Created")],
    'c_creator': ['resourceCreator', _("Object Creator")],
    'c_crossref_date': ['createTime', _("Date Submitted")],
    'c_crossref_descr': ['', _("Description")],
    'c_crossref_msg': ['', _("Required Action")],
    'c_id_issue': ['hasIssues', _("Issue")],
    'c_id_status': ['status', _("ID Status")],
    'c_identifier': ['identifier', _("Identifier")],
    'c_object_type': ['resourceType', _("Object Type")],
    'c_owner': ['owner', _("ID Owner")],
    'c_publisher': ['resourcePublisher', _("Object Publisher")],
    'c_pubyear': ['resourcePublicationYear', _("Object Publication Date")],
    'c_title': ['resourceTitle', _("Object Title")],
    'c_update_time': ['updateTime', _("ID Date Last Modified")],
}

# how to display each field, these are in custom tags for these display types
FIELD_DISPLAY_TYPES = {
    'c_create_time': 'datetime',
    'c_crossref_date': 'datetime',
    'c_identifier': 'identifier',
    'c_title': 'string',
    'c_creator': 'string',
    'c_owner': 'string',
    'c_publisher': 'string',
    'c_pubyear': 'string',
    'c_object_type': 'string',
    'c_id_status': 'string',
    'c_update_time': 'datetime',
    'c_id_issue': 'string',
    'c_crossref_descr': 'string',
    'c_crossref_msg': 'string',
}

# Table columns to choose from for given search pages, to be displayed in this order
_fieldOrderByType = {
    'public': [
        'c_title',
        'c_creator',
        'c_identifier',
        'c_publisher',
        'c_pubyear',
        'c_object_type',
    ],
    'manage': [
        'c_title',
        'c_creator',
        'c_identifier',
        'c_owner',
        'c_create_time',
        'c_update_time',
        'c_publisher',
        'c_pubyear',
        'c_object_type',
        'c_id_status',
    ],
    'issues': ['c_identifier', 'c_id_issue', 'c_title', 'c_update_time'],  # fixed
    'crossref': [  # fixed
        'c_identifier',
        'c_crossref_date',
        'c_crossref_descr',
        'c_crossref_msg',
    ],
}

# The default selected fields for display if custom fields haven't been defined
SEARCH_FIELD_DEFAULTS = _fieldOrderByType['public']
MANAGE_FIELD_DEFAULTS = operator.itemgetter(0, 1, 2, 3, 4, 5, 9)(
    _fieldOrderByType['manage']
)

DEFAULT_SORT_PRIORITY = [
    'c_update_time',
    'c_identifier',
    'c_create_time',
    'c_owner',
    'c_title',
    'c_creator',
    'c_id_status',
]

_fieldDefaultSortPriority = {
    'public': [],
    'manage': DEFAULT_SORT_PRIORITY,
    'issues': DEFAULT_SORT_PRIORITY,
    'crossref': ['c_crossref_date'],
}

IS_ASCENDING = {'asc': True, 'desc': False}
DATE_FLOOR = False
DATE_CEILING = True


def queryUrlEncoded(request):
    r = {}
    for k, v in list(queryDict(request).items()):
        if isinstance(v, str):
            v = v.encode('utf8')
        r[k] = v
    return urllib.parse.urlencode(r) if r else {}


def queryDict(request):
    """Preserve search query across requests This dictionary will be injected
    back into form fields."""
    assert request.method == "GET"
    queries = {}
    c = request.GET.copy()
    for key in c:
        if not key.startswith('c_') and not key == 'p':
            queries[key] = c[key]
    return queries if queries else {}


# noinspection PyDictCreation
def index(request):
    """(Public) Search Page."""
    if request.method != "GET":
        return impl.ui_common.methodNotAllowed(request)
    d = {'menu_item': 'ui_search.index'}
    d['collapse_advanced_search'] = "collapsed"
    d['q'] = queryDict(request)
    d['form'] = impl.form_objects.BaseSearchIdForm(d['q'])
    # if users are coming back to an advanced search, auto-open adv. search block
    if 'modify_search' in d['q'] and d['q']['modify_search'] == 't':
        if 'keywords' in d['q'] and d['q']['keywords'].strip() == '':
            d[
                'collapse_advanced_search'
            ] = ""  # Leaving this empty actually opens advanced search block
    else:
        if d['q']:
            d['p'] = 1
            d = search(d, request)
            # noinspection PySimplifyBooleanCheck
            if d['search_success'] == True:
                d['REQUEST'] = request.GET
                # noinspection PyUnresolvedReferences
                return impl.ui_common.render(request, 'search/results', d)
    # noinspection PyUnresolvedReferences
    return impl.ui_common.render(request, 'search/index', d)


# noinspection PyDictCreation
def results(request):
    """Display different page or columns from search results page."""
    d = {'menu_item': 'ui_search.results'}
    d['q'] = queryDict(request)
    d['form'] = impl.form_objects.BaseSearchIdForm(d['q'])
    d = search(d, request)
    # noinspection PyUnresolvedReferences
    return impl.ui_common.render(request, 'search/results', d)


def hasBrokenLinks(d, request):
    """Flag if any IDs are found satisfying hasIssues=true and
    linkIsBroken=true."""
    user_id, group_id = impl.ui_common.getOwnerOrGroup(
        d['owner_selected'] if 'owner_selected' in d else None
    )
    c = _buildAuthorityConstraints(request, "issues", user_id, group_id)
    c['hasIssues'] = True
    c['linkIsBroken'] = True
    return impl.open_search_util.executeSearch(
        impl.userauth.getUser(request, returnAnonymous=True), c, 0, 1
    )


def search(d, request, noConstraintsReqd=False, s_type="public"):
    """Run query and organize result set for UI, used for Search, Manage, and
    Dashboard pages.

    search function is executed from the following areas, s_type determines search
    parameters:

        Public Search (default):     ui_search   "public"
        Manage:                      ui_manage   "manage"
        Dashboard - ID Issues:       ui_admin    "issues"
        Dashboard - Crossref Status: ui_admin    "crossref"

    * noConstraintsReqd==True is used by pages that don't require form validation (dashboard, and
      manage page, whose form is unbound/unvalidated if nothing has been entered/posted.
    * If s_type=="public", don't include owner credentials in constraints.
    * 'filtered' means form fields have been submitted w/a search request
      (useful to know this for the manage page)
    * use owner or ownergroup, not both, otherwise ownergroup takes precedence
    """
    d['REQUEST'] = request.GET
    d = _pageLayout(d, request.GET, s_type)
    if noConstraintsReqd or 'form' in d and d['form'].is_valid():
        # Build dictionary of search constraints
        user_id, group_id = impl.ui_common.getOwnerOrGroup(
            d['owner_selected'] if 'owner_selected' in d else None
        )

        #
        # user_id, group_id  = 1,1
        #

        c = _buildAuthorityConstraints(request, s_type, user_id, group_id)
        if s_type in ('public', 'manage'):
            d['queries_urlencoded'] = queryUrlEncoded(
                request
            )  # Used for Google Analytics
            q = d['q'] if 'q' in d and d['q'] else request.GET
            q2 = {}
            for k, v in list(q.items()):
                q2[k] = q[k].strip() if isinstance(v, str) else q[k]
            # Move searches for IDs in keyword field to identifier field. I wanted to put this in
            # form's clean() function but unable to modify field values that route. I think I need to
            # explicitly override the form's __init__ method
            if 'keywords' in q2:
                kw = re.sub('[\"\']', '', q2['keywords'])
                if (
                    kw.lower().startswith(("doi:", "ark:/", "uuid:"))
                    and (' ' not in kw)
                    and impl.ui_common.isEmptyStr(q2.get('identifier', ''))
                ):
                    q2['keywords'] = ''
                    q2['identifier'] = kw
            if d['filtered']:
                c = _buildConstraints(c, q2, s_type)
                c = _buildTimeConstraints(c, q2, s_type)
        elif s_type == 'issues':
            d['sort'] = 'asc'  # Default sort is on update_time descending
            c['hasIssues'] = True
            c['crossref'] = False
        elif s_type == 'crossref':
            d['sort'] = 'asc'
            c['crossref'] = True
            # noinspection PyTypeChecker
            c['crossrefStatus'] = [
                Identifier.CR_RESERVED,
                Identifier.CR_WORKING,
                Identifier.CR_WARNING,
                Identifier.CR_FAILURE,
            ]
        d['total_results'] = impl.open_search_util.executeSearchCountOnly(
            impl.userauth.getUser(request, returnAnonymous=True), c
        )
        d['total_results_str'] = format(d['total_results'], "n")
        d['total_pages'] = int(math.ceil(float(d['total_results']) / float(d['ps'])))
        if d['p'] > d['total_pages']:
            d['p'] = d['total_pages']
        d['p'] = max(d['p'], 1)
        if d['order_by']:
            orderColumn = FIELDS_MAPPED[d['order_by']][0]
            if IS_ASCENDING[d['sort']]:
                orderColumn = "-" + orderColumn
        else:
            orderColumn = None
        d['results'] = []
        rec_beg = (d['p'] - 1) * d['ps']
        rec_end = d['p'] * d['ps']
        response = impl.open_search_util.executeSearch(
            impl.userauth.getUser(request, returnAnonymous=True),
            c,
            rec_beg,
            rec_end,
            orderColumn,
        )
        for hit in response.hits:
            if s_type in ('public', 'manage'):
                result = {
                    "c_create_time": datetime.fromisoformat(hit['create_time']).timestamp(),
                    "c_identifier": hit['id'],
                    "c_title": _truncateStr(hit['resource']['title']),
                    "c_creator": _truncateStr('; '.join(hit['resource']['creators'])),
                    "c_owner": hit['owner']['username'],
                    "c_object_type": hit['resource']['type'],
                    "c_publisher": _truncateStr(hit['resource']['publisher']),
                    "c_pubyear": _truncateStr(hit['resource']['publication_date']),
                    "c_id_status": impl.open_search_util.friendly_status(hit),
                    "c_update_time": datetime.fromisoformat(hit['update_time']).timestamp()
                }
                if hit['status'] == Identifier.UNAVAILABLE and hit['unavailable_reason'] != "":
                    result["c_id_status"] += " | " + hit['unavailable_reason']
            elif s_type == 'issues':
                result = {
                    "c_identifier": hit['id'],
                    "c_id_issue": "",
                    "c_title": _truncateStr(hit['resource']['title']),
                    "c_update_time": datetime.fromisoformat(hit['update_time']).timestamp(),
                }
                ir = impl.open_search_util.issue_reasons(hit)
                if ir:
                    result["c_id_issue"] += "; ".join(ir)
            elif s_type == 'crossref':
                cr_date = datetime.fromisoformat(hit['create_time']).timestamp() if hit['create_time'] \
                    else datetime.now().timestamp()
                result = {
                    "c_identifier": hit['id'],
                    "c_crossref_date": cr_date,
                    "c_crossref_descr": hit['crossref_status']
                }
                if impl.open_search_util.is_crossref_good(hit) and hit['crossref_status'] in [
                    Identifier.CR_WORKING,
                    Identifier.CR_RESERVED,
                ]:
                    result["c_crossref_msg"] = _("No action necessary")
                else:
                    result["c_crossref_msg"] = hit['crossref_message']
            # noinspection PyUnboundLocalVariable
            d['results'].append(result)
        # end of result iteration loop

        if s_type == "public":
            rec_range = '0'
            if d['total_results'] > 0:
                rec_range = (
                    str(rec_beg + 1)
                    + " "
                    + _("to")
                    + " "
                    + str(min(rec_end, d['total_results']))
                    + " "
                    + _("of")
                    + " "
                    + d['total_results_str']
                )
            d['heading_title'] = (
                _("Showing") + " " + rec_range + " " + _("Search Results")
            )
            d['search_query'] = _buildQuerySyntax(c)
        else:
            if d['filtered']:
                d['heading_title'] = d['total_results_str'] + " " + _("matches found")
            else:
                d['heading_title'] = (
                    _("Your Identifiers") + " (" + d['total_results_str'] + ")"
                )
        d['search_success'] = True
    else:  # Form did not validate
        d['collapse_advanced_search'] = ""  # Open up adv. search html block
        if '__all__' in d['form'].errors:
            # non_form_error, probably due to all fields being empty
            all_errors = ''
            errors = d['form'].errors['__all__']
            for e in errors:
                all_errors += e
            django.contrib.messages.error(
                request, _("Could not complete search.") + "   " + all_errors
            )
        else:
            err = _(
                "Could not complete search. Please check the highlighted fields below for details."
            )
            django.contrib.messages.error(request, err)
        d['search_success'] = False
    return d


def _pageLayout(d, REQUEST, s_type="public"):
    """Track user preferences for selected fields, field order, page, and page
    size."""
    d['filtered'] = False if 'filtered' not in d and 'filtered' not in REQUEST else True
    d['testPrefixes'] = django.conf.settings.TEST_SHOULDER_DICT
    d['fields_mapped'] = FIELDS_MAPPED
    d['field_display_types'] = FIELD_DISPLAY_TYPES
    f_order = _fieldOrderByType[s_type]
    d['field_order'] = f_order

    if s_type in ("issues", "crossref"):
        d['fields_selected'] = f_order
    else:
        f_defaults = (
            SEARCH_FIELD_DEFAULTS if s_type == 'public' else MANAGE_FIELD_DEFAULTS
        )
        d['jquery_checked'] = ','.join(
            ['#' + x for x in list(set(f_order) & set(f_defaults))]
        )
        d['jquery_unchecked'] = ','.join(
            ['#' + x for x in list(set(f_order) - set(f_defaults))]
        )
        d['field_defaults'] = f_defaults
        d['fields_selected'] = [x for x in f_order if x in REQUEST]
        if len(d['fields_selected']) < 1:
            d['fields_selected'] = f_defaults

    # ensure sorting defaults are set
    if 'order_by' in REQUEST and REQUEST['order_by'] in d['fields_selected']:
        d['order_by'] = REQUEST['order_by']
    elif any(
        (True for x in _fieldDefaultSortPriority[s_type] if x in d['fields_selected'])
    ):
        d['order_by'] = [
            x for x in _fieldDefaultSortPriority[s_type] if x in d['fields_selected']
        ][0]
    else:
        d['order_by'] = None
    if 'sort' in REQUEST and REQUEST['sort'] in ['asc', 'desc']:
        d['sort'] = REQUEST['sort']
    elif 'sort' not in d:
        d['sort'] = 'desc'

    # p=page and ps=pagesize -- I couldn't find an auto-paging that uses our type of models and
    # does what we want. Sorry, had to roll our own
    d['p'] = 1
    d['page_sizes'] = [10, 50, 100]
    d['ps'] = 10
    if 'p' in REQUEST and REQUEST['p'].isdigit():
        d['p'] = int(REQUEST['p'])
    if 'ps' in REQUEST and REQUEST['ps'].isdigit():
        d['ps'] = int(REQUEST['ps'])
    return d


def _buildAuthorityConstraints(request, s_type="public", owner=None, ownergroup=None):
    """A logged in user can use (public) Search page, but this would not limit
    the results to just their IDs.

    It would also include all public IDs.
    owner = username of owner; ownergroup = group name
    """
    if s_type == "public" or impl.userauth.getUser(request) is None:
        c = {'publicSearchVisible': True}
    else:
        assert owner or ownergroup, "Owner information missing"
        c = {'owner': owner} if (ownergroup is None) else {'ownergroup': ownergroup}
    return c


def _buildConstraints(c, REQUEST, s_type="public"):
    """Map form field values to values defined in DB model

    Manage Page includes additional elements. Convert unicode True/False
    to actual boolean.
    """
    cmap = {
        'keywords': 'keywords',
        'identifier': 'identifier',
        'id_type': 'identifierType',
        'title': 'resourceTitle',
        'creator': 'resourceCreator',
        'publisher': 'resourcePublisher',
        'object_type': 'resourceType',
    }
    if s_type != "public":
        cmap_managePage = {
            'target': 'target',
            'id_status': 'status',
            'harvesting': 'exported',
            'hasMetadata': 'hasMetadata',
        }
        cmap.update(cmap_managePage)
    for k, v in list(cmap.items()):
        # Handle boolean values
        if k in REQUEST and REQUEST[k] != '':
            if REQUEST[k] == 'True':
                c[v] = True
            elif REQUEST[k] == 'False':
                c[v] = False
            else:
                c[v] = REQUEST[k]
    return c


def _buildTimeConstraints(c, REQUEST, s_type="public"):
    """Add any date related constraints."""
    c = _timeConstraintBuilder(
        c, REQUEST, 'resourcePublicationYear', 'pubyear_from', 'pubyear_to'
    )
    if s_type != "public":
        c = _timeConstraintBuilder(
            c, REQUEST, 'createTime', 'create_time_from', 'create_time_to'
        )
        c = _timeConstraintBuilder(
            c, REQUEST, 'updateTime', 'update_time_from', 'update_time_to'
        )
    return c


def _timeConstraintBuilder(c, P, cname, begin, end):
    """Add time range constraints to dictionary of constraints

    cname = Name of constraint to be generated
    begin = key for begin date;   end = key for end date
    """
    if begin in P and P[begin] == '' and end in P and P[end] != '':
        c[cname] = (None, _handleDate(P[end], DATE_CEILING))
    elif begin in P and P[begin] != '':
        if end in P and P[end] != '':
            c[cname] = (
                _handleDate(P[begin], DATE_FLOOR),
                _handleDate(P[end], DATE_CEILING),
            )
        else:
            c[cname] = (_handleDate(P[begin], DATE_FLOOR), None)
    return c


def _handleDate(d, ceiling=None):
    """Convert any dates with format "YYYY-MM-DD" to Unix Timestamp."""
    if d.isdigit():
        return int(d)
    if ceiling:
        return impl.util.dateToUpperTimestamp(d)
    else:
        return impl.util.dateToLowerTimestamp(d)


def _buildQuerySyntax(c):
    """Take dictionary like this:

     {'keywords': u'marine fish', 'resourceTitle': u'"Aral Sea"'}
    and returns string like this:
     keywords:(marine AND fish) AND resourceTitle:("Aral Sea")

    Borrowing same logic from search_util.formulateQuery
     * Handling 2-tuple publication year
     * Removing characters that can't be handled by MySQL.
       For safety we remove all operators that are outside double
       quotes (i.e., quotes are the only operator we retain).
    """
    constraints = {i: c[i] for i in c if i != "publicSearchVisible"}
    r = ""
    dlength = len(constraints)
    for key, value in list(constraints.items()):
        r += key + ":"
        v = ""
        if type(value) is bool:
            r += str(value)
        elif type(value) is tuple:  # Year tuple i.e. (2001, 2002)
            # i.e. publicationYear:>=2001 AND publicationYear:<=2002
            x, y = value
            if x is not None:
                if y is not None:
                    if x == y:
                        v += str(x)
                    else:
                        v += ">=" + str(x) + " AND " + key + ":<=" + str(y)
                else:
                    v += ">=" + str(x)
            else:
                if y is not None:
                    v += "<=" + str(y)
            value = "".join(v)
            r += value
        else:  # string-based query
            value = value.strip()
            inQuote = False
            quoteOccurred = False
            r += "("
            for c in value:
                if c == '"':
                    quoteOccurred = True
                    inQuote = not inQuote
                v += c
            if inQuote:
                v += '"'
            value = "".join(v)
            vu = value.upper()
            # Just simply include 'AND' only when user hasn't used quotes or AND/OR
            if not quoteOccurred and " AND " not in vu and " OR " not in vu:
                value = re.sub(r'\\s+', ' AND ', value)
            r += value + ")"
        dlength -= 1
        if dlength >= 1:
            r += " AND "
    return r


def _truncateStr(s):
    return (s[:97] + '...') if len(s) > 97 else s
