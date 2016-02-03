import ui_common as uic
import search_util 
import django.contrib.messages
import form_objects
from django.utils.translation import ugettext as _
import math
import useradmin
 
# these are layout properties for the fields in the search and manage results pages,
# if I had realized there were going to be so many properties up front, I probably would
# have created a field layout object with a number of properties instead.

# The order to display fields both in the customize check boxes and the columns
FIELD_ORDER = ['mappedTitle', 'mappedCreator', 'identifier', 'owner', 'createTime',\
               'updateTime', 'status']

# The default selected fields for display if custom fields haven't been defined
FIELD_DEFAULTS = ['mappedTitle', 'mappedCreator', 'identifier', 'owner', 'createTime',\
                  'updateTime', 'status']

# Column names for display for each field
FIELDS_MAPPED = {'identifier':_("Identifier"),  'owner':_("Owner"), 'coOwners':_("Co-Owners"), \
                  'createTime':_("Date Created"), 'updateTime':_("Date Last Modified"), \
                  'status':_("Status"), 'mappedTitle':_("Object Title"), \
                  'mappedCreator':_("Object Creator")}

#how to display each field, these are in custom tags for these display types
FIELD_DISPLAY_TYPES = {'identifier': 'identifier',  'owner': 'string', 'coOwners': 'coowners', \
                'createTime': 'datetime', 'updateTime': 'datetime', 'status' :'string',\
                'mappedTitle': 'string', 'mappedCreator' : 'string'}

# priority for the sort order if it is not set, choose the first field that exists in this order
FIELD_DEFAULT_SORT_PRIORITY = ['updateTime', 'identifier', 'createTime', 'owner', 'mappedTitle', \
                'mappedCreator', 'status', 'coOwners']

IS_ASCENDING = {'asc': True, 'desc': False }

def index(request):
  """ (Public) Search Page """
  d = { 'menu_item' : 'ui_search.index' }
  if request.method == "GET":
    d['form'] = form_objects.BaseSearchIdForm() # Build an empty form
  elif request.method == "POST":
    d['form'] = form_objects.BaseSearchIdForm(request.POST)
    noConstraintsReqd = False
    d = searchIdentifiers(d, request, noConstraintsReqd)
    if d['search_success'] == True:
      return uic.render(request, 'search/results', d)
  return uic.render(request, 'search/index', d)

def searchIdentifiers(d, request, noConstraintsReqd=False, isPublicSearch=True):
  """ 
  Run query and organize result set for UI, used for both Search page and 
  Manage Search page, the latter of which works with slightly larger set of constraints.
  If noConstraintsReqd==True, provide a result set even though form itself is empty.
  If isPublicSearch==True, don't include owner credentials in constraints.
  """
  if d['form'].is_valid() or noConstraintsReqd:
    if request.method == "GET":
      REQUEST = request.GET
    else:
      REQUEST = request.POST
    d['testPrefixes'] = uic.testPrefixes
    d['jquery_checked'] = ','.join(['#' + x for x in list(set(FIELD_ORDER) & set(FIELD_DEFAULTS))])
    d['jquery_unchecked'] = ','.join(['#' + x for x in list(set(FIELD_ORDER) - set(FIELD_DEFAULTS))])
    # r = useradmin.getAccountProfile(request.session["auth"].user[0])
    # if 'ezidCoOwners' in r:
    #   d['account_co_owners'] = r['ezidCoOwners']
    # else:
    d['account_co_owners'] = ''
    d['field_order'] = FIELD_ORDER
    d['field_norewrite'] = FIELD_ORDER + ['includeCoowned']
    d['fields_mapped'] = FIELDS_MAPPED
    d['field_defaults'] = FIELD_DEFAULTS
    # ToDo: Map fields approprately from both customize and from Search Query
    # d['fields_selected'] = [x for x in FIELD_ORDER if x in REQUEST ]
    # Temporary setup:
    # if len(d['fields_selected']) < 1: 
    d['fields_selected'] = FIELD_DEFAULTS
    d['REQUEST'] = REQUEST 
    d['field_display_types'] = FIELD_DISPLAY_TYPES

    #ensure sorting defaults are set
    d['includeCoowned'] = True
    if 'submit_checks' in REQUEST and not ('includeCoowned' in REQUEST):
      d['includeCoowned'] = False    
    if 'order_by' in REQUEST and REQUEST['order_by'] in d['fields_selected']:
      d['order_by'] = REQUEST['order_by']
    else:
      d['order_by'] = [x for x in FIELD_DEFAULT_SORT_PRIORITY if x in d['fields_selected'] ][0]
    if 'sort' in REQUEST and REQUEST['sort'] in ['asc', 'desc']:
      d['sort'] = REQUEST['sort']
    else:
      d['sort'] = 'desc'
    #p=page and ps=pagesize -- I couldn't find an auto-paging that uses our type of models and 
    #does what we want. Sorry, had to roll our own
    d['p'] = 1
    d['ps'] = 10
    if 'p' in REQUEST and REQUEST['p'].isdigit(): d['p'] = int(REQUEST['p'])
    if 'ps' in REQUEST and REQUEST['ps'].isdigit(): d['ps'] = int(REQUEST['ps'])

    # Build dictionary of search constraints
    c = _buildAuthorityConstraints(request, isPublicSearch)
    if not noConstraintsReqd:
      c = _buildConstraints(c, REQUEST, isPublicSearch)
      c = _buildTimeConstraints(c, REQUEST, isPublicSearch)
    d['search_query'] = _buildQuerySyntax(c)
    d['total_results'] = search_util.formulateQuery(c).count()
    d['total_pages'] = int(math.ceil(float(d['total_results'])/float(d['ps'])))
    if d['p'] > d['total_pages']: d['p'] = d['total_pages']
    d['p'] = max(d['p'], 1)
    orderColumn = d['order_by']
    if orderColumn in ["mappedTitle", "mappedCreator"]:
      orderColumn = "resource" + orderColumn[6:] + "Prefix"
    elif orderColumn == "coOwners":
      orderColumn = "updateTime" # arbitrary; co-owners not supported anymore
    if not IS_ASCENDING[d['sort']]: orderColumn = "-" + orderColumn
    d['results'] = []
    # ToDo:  Greg also had this in his query for Manage Page:  select_related("owner").\
    for id in search_util.formulateQuery(c, orderBy=orderColumn)\
      [(d['p']-1)*d['ps']:d['p']*d['ps']]:
      result = { "identifier": id.identifier, "owner": id.owner.username,
        "coOwners": "", "createTime": id.createTime,
        "updateTime": id.updateTime, "status": id.get_status_display(),
        "mappedTitle": id.resourceTitle, "mappedCreator": id.resourceCreator }
      if id.isUnavailable and id.unavailableReason != "":
        result["status"] += " | " + id.unavailableReason
      d['results'].append(result)
    d['search_success'] = True
  else:
    d['show_advanced_search'] = "in" # Class name opens up adv. search html block
    if '__all__' in d['form'].errors:
      # non_form_error, probably due to all fields being empty
      all_errors = ''
      errors = d['form'].errors['__all__']
      for e in errors:
        all_errors += e 
      django.contrib.messages.error(request, _("Could not complete search.   " + all_errors))
    else:
      django.contrib.messages.error(request, _("Could not complete search.  ") +\ 
        _("Please check the highlighted fields below for details."))
    d['search_success'] = False 
  return d

def results(request):
  d = { 'menu_item' : 'ui_search.results' } 
  return uic.render(request, 'search/results', d)

def _buildAuthorityConstraints(request, isPublicSearch=True):
  """ 
  A logged in user can use (public) Search page, but this would not limit the
  results to just their IDs. It would also include all public IDs.
  """
  if isPublicSearch or "auth" not in request.session:
    c = {'publicSearchVisible': True}
  else:
    c = {'owner': request.session['auth'].user[0]}
  return c

def _buildConstraints(c, REQUEST, isPublicSearch=True):
  """ Map form field values to values defined in DB model.
      Manage Page includes additional elements. """
  cmap = {'keywords': 'keywords', 'identifier': 'identifier', 
    'id_type': 'identifierType', 'title': 'resourceTitle', 
    'creator': 'resourceCreator', 'publisher': 'resourcePublisher', 
    'object_type': 'resourceType'}
  if not isPublicSearch:
    cmap_managePage = {'target': 'target', 'id_status': 'status',
      'harvesting': 'exported', 'hasMetadata': 'hasMetadata'}
    cmap.update(cmap_managePage)
  for k,v in cmap.iteritems(): 
    if k in REQUEST and REQUEST[k]!='': c[v] = REQUEST[k].strip()
  return c

def _buildTimeConstraints(c, REQUEST, isPublicSearch=True):
  """ Add any date related constraints """
  c = _timeConstraintBuilder(c, REQUEST, 'resourcePublicationYear', 'pubyear_from', 'pubyear_to')
  if not isPublicSearch:
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
      c[cname] = (None,int(P[end]))
  elif begin in P and P[begin]!='':
    if end in P and P[end]!='':
      c[cname] = (int(P[begin]),int(P[end]))
    else:
      c[cname] = (int(P[begin]),None)
  return c

def _buildQuerySyntax(c):
  """ Takes dictionary like this:
       {'keywords': u'marine fish', 'resourceTitle': u'"Aral Sea"'}
      and returns string like this:
       keywords:(marine OR fish) AND title:("Aral Sea")

      Borrowing same logic from search_util.formulateQuery
      in terms of removing characters that can't be hanled by MySQL.
      For safety we remove all operators that are outside double 
      quotes (i.e., quotes are the only operator we retain).
  """
  constraints = {i:c[i] for i in c if i!="publicSearchVisible"}
  r = ""
  dlength = len(constraints)
  for key,value in constraints.items():
    r += key + ":("
    v = ""
    inQuote = False
    quoteOccurred = False
    for c in value:
      if c == '"':
        quoteOccurred = True
        inQuote = not inQuote
      else:
        if not inQuote and not c.isalnum() and c!=" ": c = ""
      v += c
    if inQuote: v += '"'
    value = "".join(v)
    # Being simplistic about how to treat quoted queries
    if not quoteOccurred:
      value = value.replace(" ", " OR ") 
    r += value + ")"
    dlength -= 1
    if dlength >= 1: r += " AND "
  return r 
