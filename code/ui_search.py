import ui_common as uic
import ezidapp.models
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
    d['form'] = form_objects.SearchForm() # Build an empty form
    return uic.render(request, 'search/index', d)
  elif request.method == "POST":
    REQUEST = request.POST
    d['form'] = form_objects.SearchForm(request.POST)
    if d['form'].is_valid():
      """ This code is duplicated from ui_manage. So:
          ToDo:  this needs to be refactored/reduced. 
          Temporarily spit out all IDs for current user """
      d['testPrefixes'] = uic.testPrefixes
      d['jquery_checked'] = ','.join(['#' + x for x in list(set(FIELD_ORDER) & set(FIELD_DEFAULTS))])
      d['jquery_unchecked'] = ','.join(['#' + x for x in list(set(FIELD_ORDER) - set(FIELD_DEFAULTS))])
      d['user'] = request.session['auth'].user
      r = useradmin.getAccountProfile(request.session["auth"].user[0])
      if 'ezidCoOwners' in r:
        d['account_co_owners'] = r['ezidCoOwners']
      else:
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
      # ToDo: This query is still missing identifier and identifier type
      d['total_results'] = ezidapp.models.SearchIdentifier.objects.\
        filter(owner__username=d['user'][0]).\
        filter(keywords=REQUEST['keywords']).\
        filter(resourceTitle=REQUEST['title']).\
        filter(resourceCreator=REQUEST['creator']).\
        filter(resourcePublisher=REQUEST['publisher']).\
        filter(resourcePublicationDate__gte=REQUEST['pubdate_from']).\
        filter(resourcePublicationDate__lte=REQUEST['pubdate_to']).\
        filter(resourceType=REQUEST['object_type']).count()
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
      for id in ezidapp.models.SearchIdentifier.objects.\
        filter(owner__username=d['user'][0]).\
        filter(keywords=REQUEST['keywords']).\
        filter(resourceTitle=REQUEST['title']).\
        filter(resourceCreator=REQUEST['creator']).\
        filter(resourcePublisher=REQUEST['publisher']).\
        filter(resourcePublicationDate__gte=REQUEST['pubdate_from']).\
        filter(resourcePublicationDate__lte=REQUEST['pubdate_to']).\
        filter(resourceType=REQUEST['object_type']).count()
        only("identifier", "owner__username", "createTime", "updateTime",
        "status", "unavailableReason", "resourceTitle", "resourceCreator").\
        select_related("owner").\
        order_by(orderColumn)[(d['p']-1)*d['ps']:d['p']*d['ps']+DEBUG_PAGING]:
        # ToDo: Discuss with Greg how to chunk large result sets for performance reasons
        # Jquery table doesn't require chunking
        result = { "identifier": id.identifier, "owner": id.owner.username,
          "coOwners": "", "createTime": id.createTime,
          "updateTime": id.updateTime, "status": id.get_status_display(),
          "mappedTitle": id.resourceTitle, "mappedCreator": id.resourceCreator }
        if id.isUnavailable and id.unavailableReason != "":
          result["status"] += " | " + id.unavailableReason
        d['results'].append(result)
      return uic.render(request, 'search/results', d)
    else:
      all_errors = ''
      errors = d['form'].errors['__all__']
      for e in errors:
        all_errors += e 
      django.contrib.messages.error(request, _("Could not complete search.   " + all_errors))
      return uic.render(request, 'search/index', d)

def results(request):
  d = { 'menu_item' : 'ui_search.results' } 
  return uic.render(request, 'search/results', d)
