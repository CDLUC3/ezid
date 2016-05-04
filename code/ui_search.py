import ui_common as uic
import search_util 
import django.contrib.messages
import form_objects
from django.utils.translation import ugettext as _
import math
import locale
import util
import operator
import re
locale.setlocale(locale.LC_ALL, '')

# Search is executed from the following areas, and these names determine search parameters:
# Public Search:               ui_search   "public"
# Manage:                      ui_manage   "manage"
# Dashboard - ID Issues:       ui_admin    "issues"
# Dashboard - CrossRef Status: ui_admin    "crossref"

# Form fields from search are defined in code/form_objects.py.
# Corresponding fields used for column display include a 'c_' prefix.

#######     LAYOUT PROPERTIES     #########
# if I had realized there were going to be so many properties up front, I probably would
# have created a field layout object with a number of properties instead.

# Column IDs mapped to 1) DB constraints names and 2) UI display
FIELDS_MAPPED = {
  'c_create_time':        ['createTime',          _("ID Date Created")], 
  'c_creator':            ['resourceCreator',     _("Object Creator")],
  'c_crossref_date':      ['',                    _("Date Submitted")], # i.e. createTime 
  'c_crossref_descr':     ['',                    _("Description")],
  'c_crossref_msg':       ['',                    _("Required Action")],
  'c_id_issue':           ['hasIssues',           _("Issue")],
  'c_id_status':          ['status',              _("ID Status")],
  'c_identifier':         ['identifier',          _("Identifier")], 
  'c_object_type':        ['resourceType',        _("Object Type")],
  'c_owner':              ['owner',               _("ID Owner")],
  'c_publisher':          ['resourcePublisher',   _("Object Publisher")],
  'c_pubyear':            ['resourcePublicationYear', _("Object Publication Date")],
  'c_title':              ['resourceTitle',       _("Object Title")], 
  'c_update_time':        ['updateTime',          _("ID Date Last Modified")],
}

#how to display each field, these are in custom tags for these display types
FIELD_DISPLAY_TYPES = {
  'c_create_time': 'datetime', 'c_crossref_date': 'datetime', 'c_identifier': 'identifier',
  'c_title': 'string', 'c_creator' : 'string', 'c_owner': 'string', 'c_publisher': 'string',\
  'c_pubyear': 'string', 'c_object_type': 'string', 'c_id_status' :'string',\
  'c_update_time': 'datetime', 'c_id_issue': 'string', 'c_crossref_descr': 'string',\
  'c_crossref_msg': 'string'
}

# Table columns to choose from for given search pages, to be displayed in this order
_fieldOrderByType = {
  'public':
          ['c_title', 'c_creator', 'c_identifier', 'c_publisher', 'c_pubyear', 'c_object_type'],
  'manage':
          ['c_title', 'c_creator', 'c_identifier', 'c_owner', 'c_create_time', 'c_update_time',\
           'c_publisher', 'c_pubyear', 'c_object_type', 'c_id_status'],
  'issues':   # fixed
          ['c_identifier', 'c_id_issue', 'c_title', 'c_update_time'],
  'crossref':    # fixed
          ['c_identifier', 'c_crossref_date', 'c_crossref_descr', 'c_crossref_msg']
}

# The default selected fields for display if custom fields haven't been defined
SEARCH_FIELD_DEFAULTS = _fieldOrderByType['public']
MANAGE_FIELD_DEFAULTS = operator.itemgetter(0,1,2,3,4,5,9)(_fieldOrderByType['manage'])

DEFAULT_SORT_PRIORITY = ['c_update_time', 'c_identifier', 'c_create_time', \
                'c_owner', 'c_title', 'c_creator', 'c_id_status']

_fieldDefaultSortPriority = {
  'public': [],
  'manage': DEFAULT_SORT_PRIORITY,
  'issues': DEFAULT_SORT_PRIORITY,
  'crossref': DEFAULT_SORT_PRIORITY }

IS_ASCENDING = {'asc': True, 'desc': False }
DATE_FLOOR = False 
DATE_CEILING = True 

def queryDict(request):
  """
  Preserve search query across get requests 
  This dictionary will be injected back into form fields
  """
  assert request.method == "GET"
  queries = {}
  c = request.GET.copy()
  for key in c:
    if not key.startswith('c_') and not key == 'p':
      queries[key] = c[key]
  return queries if queries else {}

def index(request):
  """ (Public) Search Page """
  d = { 'menu_item' : 'ui_search.index' }
  d['show_advanced_search'] = "closed"
  if request.method == "GET":
    d['queries'] = queryDict(request)
    # if users are coming back to an advanced search, auto-open adv. search block
    if d['queries'] and d['queries']['keywords'].strip() == '':
      d['show_advanced_search'] = "open"
    d['form'] = form_objects.BaseSearchIdForm(d['queries'])
    d['REQUEST'] = request.GET 
    d = _pageLayout(d, request.GET)
  elif request.method == "POST":
    d['p'] = 1
    d['form'] = form_objects.BaseSearchIdForm(request.POST)
    d = search(d, request)
    if d['search_success'] == True:
      return uic.render(request, 'search/results', d)
  return uic.render(request, 'search/index', d)

def results(request):
  """ Display different page or columns from search results page """
  d = { 'menu_item' : 'ui_search.results' } 
  if request.method == "GET":
    d['queries'] = queryDict(request)
    d['form'] = form_objects.BaseSearchIdForm(d['queries'])
  d = search(d, request)
  return uic.render(request, 'search/results', d)

def search(d, request, noConstraintsReqd=False, s_type="public"):
  """ 
  Run query and organize result set for UI, used for Search, Manage, and Dashboard pages.
  * noConstraintsReqd==True is used by pages that don't require form validation (dashboard, and
    manage page, whose form is unbound/unvalidated if nothing has been entered/posted.
  * If s_type=="public", don't include owner credentials in constraints.
  * 'filtered' means form fields have been submitted w/a search request 
    (useful to know this for the manage page)
  """
  if request.method == "GET":
    REQUEST = request.GET
  else:
    REQUEST = request.POST
  d['REQUEST'] = REQUEST 
  d = _pageLayout(d, REQUEST, s_type)
  if noConstraintsReqd or 'form' in d and d['form'].is_valid():
    # Build dictionary of search constraints
    c = _buildAuthorityConstraints(request, s_type)
    if s_type in ('public', 'manage'):
      q = d['queries'] if 'queries' in d and d['queries'] else REQUEST
      q2 = {}
      for k,v in q.iteritems():
        q2[k] = q[k].strip() if isinstance(v, basestring) else q[k]
      if d['filtered']:
        c = _buildConstraints(c, q2, s_type)
        c = _buildTimeConstraints(c, q2, s_type)
    elif s_type == 'issues':
      c['hasIssues'] = True
    elif s_type == 'crossref':
      c['crossref'] = True
    d['total_results'] = search_util.formulateQuery(c).count()
    d['total_results_str'] = format(d['total_results'], "n") 
    d['total_pages'] = int(math.ceil(float(d['total_results'])/float(d['ps'])))
    if d['p'] > d['total_pages']: d['p'] = d['total_pages']
    d['p'] = max(d['p'], 1)
    if d['order_by']:
      orderColumn = FIELDS_MAPPED[d['order_by']][0]
      if IS_ASCENDING[d['sort']]: orderColumn = "-" + orderColumn
    else:
      orderColumn = None
    d['results'] = []
    # ToDo:  Add in ownership constraints (user, proxy, etc)
    rec_beg = (d['p']-1)*d['ps']
    rec_end = d['p']*d['ps']
    for id in search_util.formulateQuery(c, orderBy=orderColumn)[rec_beg:rec_end]:
      if s_type in ('public', 'manage'):
        result = {
          "c_create_time": id.createTime,
          "c_identifier": id.identifier,
          "c_title": id.resourceTitle,
          "c_creator": id.resourceCreator,
          "c_owner": id.owner.username,
          "c_object_type": id.resourceType,
          "c_publisher": id.resourcePublisher,
          "c_pubyear": id.resourcePublicationDate,
          "c_id_status": id.get_status_display(),
          "c_update_time": id.updateTime,
        }
        if id.isUnavailable and id.unavailableReason != "":
          result["c_id_status"] += " | " + id.unavailableReason
      elif s_type == 'issues':
        result = {
          "c_identifier": id.identifier,
          "c_id_issue": "",
          "c_title": id.resourceTitle,
          "c_update_time": id.updateTime,
        }
        ir = id.issueReasons()
        if ir:
          result["c_id_issue"] += ";".join(ir)
      elif s_type == 'crossref':
        if id.isCrossrefGood and id.crossrefStatus not in [id.CR_WORKING, id.CR_RESERVED]:
          continue 
        else:
          result = {
            "c_identifier": id.identifier,
            "c_crossref_date": id.createTime,
            "c_crossref_descr": id.get_crossrefStatus_display(),
          }
          if id.isCrossrefGood and id.crossrefStatus in [id.CR_WORKING, id.CR_RESERVED]:
            result["c_crossref_msg"] = _("No action necessary")
          else:
            result["c_crossref_msg"] = id.crossrefMessage 
      d['results'].append(result)
    # end of result iteration loop 
    if s_type == "public":
      rec_range = '0' 
      if d['total_results'] > 0:
        rec_range = str(rec_beg + 1) +  " " + _("to") +  " " +\
           str(min(rec_end, d['total_results'])) + " " + _("of") + " " +  d['total_results_str']
      d['heading_title'] = _("Showing") +  " " + rec_range + " " +  _("Search Results")
      d['search_query'] = _buildQuerySyntax(c)
    else:
      if d['filtered']:
        d['heading_title'] = d['total_results_str'] + " " + _("matches found")
      else:
        d['heading_title'] = _("Your Identifiers") + " (" + d['total_results_str'] + ")"
    d['search_success'] = True
  else:  # Form did not validate
    d['show_advanced_search'] = "open" # Open up adv. search html block
    if '__all__' in d['form'].errors:
      # non_form_error, probably due to all fields being empty
      all_errors = ''
      errors = d['form'].errors['__all__']
      for e in errors:
        all_errors += e 
      django.contrib.messages.error(request, _("Could not complete search.") + "   " + all_errors)
    else:
      err = _("Could not complete search.  Please check the highlighted fields below for details.")
      django.contrib.messages.error(request, err) 
    d['search_success'] = False 
  return d

def _pageLayout(d, REQUEST, s_type="public"):
  """
  Track user preferences for selected fields, field order, page, and page size
  """
  d['filtered'] = True if 'filtered' in REQUEST else False
  d['testPrefixes'] = uic.testPrefixes
  d['fields_mapped'] = FIELDS_MAPPED
  d['field_display_types'] = FIELD_DISPLAY_TYPES
  f_order = _fieldOrderByType[s_type] 
  d['field_order'] = f_order 

  if s_type in ("issues", "crossref"):
    d['fields_selected'] = f_order 
  else:
    f_defaults = SEARCH_FIELD_DEFAULTS if s_type == 'public' else MANAGE_FIELD_DEFAULTS
    d['jquery_checked'] = ','.join(['#' + x for x in list(set(f_order) & set(f_defaults))])
    d['jquery_unchecked'] = ','.join(['#' + x for x in list(set(f_order) - set(f_defaults))])
    d['field_defaults'] = f_defaults 
    d['fields_selected'] = [x for x in f_order if x in REQUEST ]
    if len(d['fields_selected']) < 1: d['fields_selected'] = f_defaults 

  #ensure sorting defaults are set
  if 'order_by' in REQUEST and REQUEST['order_by'] in d['fields_selected']:
    d['order_by'] = REQUEST['order_by']
  elif any((True for x in _fieldDefaultSortPriority[s_type] if x in d['fields_selected'])):
    d['order_by'] = [x for x in _fieldDefaultSortPriority[s_type] if x in d['fields_selected'] ][0]
  else:
    d['order_by'] = None 
  if 'sort' in REQUEST and REQUEST['sort'] in ['asc', 'desc']:
    d['sort'] = REQUEST['sort']
  elif 'sort' not in d:
    d['sort'] = 'desc'

  #p=page and ps=pagesize -- I couldn't find an auto-paging that uses our type of models and 
  #does what we want. Sorry, had to roll our own
  d['p'] = 1
  d['page_sizes'] = [10, 50, 100]
  d['ps'] = 10
  if 'p' in REQUEST and REQUEST['p'].isdigit(): d['p'] = int(REQUEST['p'])
  if 'ps' in REQUEST and REQUEST['ps'].isdigit(): d['ps'] = int(REQUEST['ps'])
  return d

def _buildAuthorityConstraints(request, s_type="public"):
  """ 
  A logged in user can use (public) Search page, but this would not limit the
  results to just their IDs. It would also include all public IDs.
  """
  if s_type == "public" or "auth" not in request.session:
    c = {'publicSearchVisible': True}
  else:
    c = {'owner': request.session['auth'].user[0]}
  return c

def _buildConstraints(c, REQUEST, s_type="public"):
  """ Map form field values to values defined in DB model.
      Manage Page includes additional elements. 
      Convert unicode True/False to actual boolean."""
  cmap = {'keywords': 'keywords', 'identifier': 'identifier', 
    'id_type': 'identifierType', 'title': 'resourceTitle', 
    'creator': 'resourceCreator', 'publisher': 'resourcePublisher', 
    'object_type': 'resourceType'}
  if s_type != "public":
    cmap_managePage = {'target': 'target', 'id_status': 'status',
      'harvesting': 'exported', 'hasMetadata': 'hasMetadata'}
    cmap.update(cmap_managePage)
  for k,v in cmap.iteritems(): 
    # Handle boolean values
    if k in REQUEST and REQUEST[k]!='': 
      if   REQUEST[k] == u'True':    c[v] = True
      elif REQUEST[k] == u'False':   c[v] = False 
      else:                          c[v] = REQUEST[k]
  return c

def _buildTimeConstraints(c, REQUEST, s_type="public"):
  """ Add any date related constraints """
  c = _timeConstraintBuilder(c, REQUEST, 'resourcePublicationYear', 'pubyear_from', 'pubyear_to')
  if s_type != "public":
    c = _timeConstraintBuilder(c, REQUEST, 'createTime', 'create_time_from', 'create_time_to')
    c = _timeConstraintBuilder(c, REQUEST, 'updateTime', 'update_time_from', 'update_time_to')
  return c

def _timeConstraintBuilder(c, P, cname, begin, end):
  """ Adds time range constraints to dictionary of constraints. 
      cname = Name of constraint to be generated
      begin = key for begin date;   end = key for end date
  """
  if begin in P and P[begin]=='' and \
    end in P and P[end]!='':
      c[cname] = (None, _handleDate(P[end], DATE_CEILING))
  elif begin in P and P[begin]!='':
    if end in P and P[end]!='':
      c[cname] = (_handleDate(P[begin], DATE_FLOOR), _handleDate(P[end], DATE_CEILING))
    else:
      c[cname] = (_handleDate(P[begin], DATE_FLOOR), None)
  return c

def _handleDate(d, ceiling=None):
  """ Convert any dates with format "YYYY-MM-DD" to Unix Timestamp"""
  if d.isdigit(): return int(d)
  if ceiling:
    return util.dateToUpperTimestamp(d)
  else:
    return util.dateToLowerTimestamp(d)

def _buildQuerySyntax(c):
  """ Takes dictionary like this:
       {'keywords': u'marine fish', 'resourceTitle': u'"Aral Sea"'}
      and returns string like this:
       keywords:(marine OR fish) AND title:("Aral Sea") 

      Borrowing same logic from search_util.formulateQuery
       * Handling 2-tuple publication year
       * Removing characters that can't be handled by MySQL.
         For safety we remove all operators that are outside double 
         quotes (i.e., quotes are the only operator we retain).
  """
  constraints = {i:c[i] for i in c if i!="publicSearchVisible"}
  r = ""
  dlength = len(constraints)
  for key,value in constraints.items():
    r += key + ":"
    v = ""
    if type(value) is bool:
      r += str(value)
    elif type(value) is tuple:  # Year tuple i.e. (2001, 2002)
      # i.e. publicationYear:>=2001 AND publicationYear:<=2002
      x,y = value 
      if x != None:
        if y != None:
          if x == y:
            v += str(x) 
          else:
            v += ">=" + str(x) + " AND " + key + ":<=" + str(y) 
        else:
          v += ">=" + str(x) 
      else:
        if y != None:
          v += "<=" + str(y) 
      value = "".join(v)
      r += value
    else:    # string-based query
      value = value.strip()
      inQuote = False
      quoteOccurred = False
      r += "("
      for c in value:
        if c == '"':
          quoteOccurred = True
          inQuote = not inQuote
        v += c
      if inQuote: v += '"'
      value = "".join(v)
      # Being simplistic about how to treat quoted queries
      if not quoteOccurred:
        value = re.sub(r'\s+', ' OR ', value)
      r += value + ")"
    dlength -= 1
    if dlength >= 1: r += " AND "
  return r 
