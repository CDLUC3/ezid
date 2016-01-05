import ui_common as uic
import search_util 
import django.contrib.messages
import form_objects
from django.utils.translation import ugettext as _
import math
import useradmin
 
DEBUG_PAGING = 3

# these are layout properties for the fields in the manage index page,
# if I had realized there were going to be so many properties up front, I probably would
# have created a field layout object with a number of properties instead.

# The order to display fields both in the customize check boxes and the columns
FIELD_ORDER = ['mappedTitle', 'mappedCreator', 'identifier', 'owner', 'createTime',\
               'updateTime', 'status']

# The default selected fields for display if custom fields haven't been defined
FIELD_DEFAULTS = ['mappedTitle', 'mappedCreator', 'identifier', 'owner', 'createTime',\
                  'updateTime', 'status']

# Column names for display for each field
FIELDS_MAPPED = {'identifier':'Identifier',  'owner':'Owner', 'coOwners': 'Co-Owners', \
                  'createTime': 'Date Created', 'updateTime': 'Date Last Modified', 'status' :'Status',\
                  'mappedTitle': 'Object Title', 'mappedCreator' : 'Object Creator'}

# Weight to give each field for table display since many or few fields are present and can be customized
FIELD_WIDTHS = {'identifier': 2.0,  'owner': 1.0, 'coOwners': 2.0, \
                'createTime': 2.0, 'updateTime': 2.0, 'status' :1.0,\
                'mappedTitle': 3.0, 'mappedCreator' : 2.0}

#how to display each field, these are in custom tags for these display types
FIELD_DISPLAY_TYPES = {'identifier': 'identifier',  'owner': 'string', 'coOwners': 'coowners', \
                'createTime': 'datetime', 'updateTime': 'datetime', 'status' :'string',\
                'mappedTitle': 'string', 'mappedCreator' : 'string'}

# priority for the sort order if it is not set, choose the first field that exists in this order
FIELD_DEFAULT_SORT_PRIORITY = ['updateTime', 'identifier', 'createTime', 'owner', 'mappedTitle', \
                'mappedCreator', 'status', 'coOwners']

IS_ASCENDING = {'asc': True, 'desc': False }

def index(request):
  d = { 'menu_item' : 'ui_search.index' }
  if request.method == "GET":
    d['form'] = form_objects.BaseSearchForm() # Build an empty form
    return uic.render(request, 'search/index', d)
  elif request.method == "POST":
    REQUEST = request.POST
    d['form'] = form_objects.BaseSearchForm(request.POST)
    if d['form'].is_valid():
      """ This code is duplicated from ui_manage. So:
          ToDo:  this needs to be refactored/reduced. 
          Temporarily spit out all IDs for current user """
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
      d['fields_selected'] = FIELD_DEFAULTS
      d['REQUEST'] = REQUEST
      d['field_widths'] = FIELD_WIDTHS
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
      #p=page and ps=pagesize -- I couldn't find an auto-paging that uses our type of models and does what we want
      #sorry, had to roll our own
      d['p'] = 1
      d['ps'] = 10
      if 'p' in REQUEST and REQUEST['p'].isdigit(): d['p'] = int(REQUEST['p'])
      if 'ps' in REQUEST and REQUEST['ps'].isdigit(): d['ps'] = int(REQUEST['ps'])
      # dictionary of search constraints
      c = _buildAuthorityConstraints(request)
      c = _buildConstraints(c, REQUEST)
      c = _buildTimeConstraints(c, REQUEST)
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
      # ToDo: This query is still missing identifier and identifier type
      for id in search_util.formulateQuery(c, orderBy=orderColumn)\
        [(d['p']-1)*d['ps']:d['p']*d['ps']+DEBUG_PAGING]:
        result = { "identifier": id.identifier, "owner": id.owner.username,
          "coOwners": "", "createTime": id.createTime,
          "updateTime": id.updateTime, "status": id.get_status_display(),
          "mappedTitle": id.resourceTitle, "mappedCreator": id.resourceCreator }
        if id.isUnavailable and id.unavailableReason != "":
          result["status"] += " | " + id.unavailableReason
        d['results'].append(result)
      return uic.render(request, 'search/results', d)
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
        django.contrib.messages.error(request, _("Could not complete search. \
          Please check the highlighted fields below for details."))
      return uic.render(request, 'search/index', d)

def _buildAuthorityConstraints(request):
  if "auth" not in request.session:
    c = {'publicSearchVisible': True}
  else:
    c = {'owner': request.session['auth'].user[0]}
  return c

def _buildConstraints(c, REQUEST):
  """ Map form field values to values defined in DB model """
  cmap = {'keywords': 'keywords', 'identifier': 'identifier', 
    'id_type': 'identifierType', 'title': 'resourceTitle', 
    'creator': 'resourceCreator', 'publisher': 'resourcePublisher', 
    'object_type': 'resourceType'}
  for k,v in cmap.iteritems(): 
    if k in REQUEST and REQUEST[k]!='': c[v] = REQUEST[k]
  return c

def _buildTimeConstraints(c, REQUEST):
  """ Add any date related constraints """
  if 'pubyear_from' in REQUEST and REQUEST['pubyear_from']=='' and \
    'pubyear_to' in REQUEST and REQUEST['pubyear_to']!='':
      c['resourcePublicationYear'] = (None,int(REQUEST['pubyear_to']))
  elif 'pubyear_from' in REQUEST and REQUEST['pubyear_from']!='':
    if 'pubyear_to' in REQUEST and REQUEST['pubyear_to']!='':
      c['resourcePublicationYear'] = (int(REQUEST['pubyear_from']),int(REQUEST['pubyear_to']))
    else:
      c['resourcePublicationYear'] = (int(REQUEST['pubyear_from']),None)
  return c

def results(request):
  d = { 'menu_item' : 'ui_search.results' } 
  return uic.render(request, 'search/results', d)

