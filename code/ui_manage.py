import ui_common as uic
import django.contrib.messages
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
import ezid
import metadata
import search
import math
import useradmin
import erc
import datacite
import urllib


# these are layout properties for the fields in the manage index page,
# if I had realized there were going to be so many properties up front, I probably would
# have created a field layout object with a number of properties instead.

# The order to display fields both in the customize check boxes and the columns
FIELD_ORDER = ['identifier', 'owner', 'coOwners', 'createTime', 'updateTime', 'status',\
                'mappedTitle', 'mappedCreator']

# The default selected fields for display if custom fields haven't been defined
FIELD_DEFAULTS = ['identifier', 'createTime', 'mappedTitle', 'mappedCreator']

# Column names for display for each field
FIELDS_MAPPED = {'identifier':'ID',  'owner':'Owner', 'coOwners': 'Co-Owners', \
                  'createTime': 'Date created', 'updateTime': 'Date last modified', 'status' :'Status',\
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
FIELD_DEFAULT_SORT_PRIORITY = ['identifier', 'createTime', 'updateTime', 'owner', 'mappedTitle', \
                'mappedCreator', 'status', 'coOwners']

IS_ASCENDING = {'asc': True, 'desc': False }

@uic.user_login_required
def index(request):
  d = { 'menu_item' : 'ui_manage.index' }
  d['testPrefixes'] = uic.testPrefixes
  d['jquery_checked'] = ','.join(['#' + x for x in list(set(FIELD_ORDER) & set(FIELD_DEFAULTS))])
  d['jquery_unchecked'] = ','.join(['#' + x for x in list(set(FIELD_ORDER) - set(FIELD_DEFAULTS))])
  d['user'] = request.session['auth'].user
  r = useradmin.getAccountProfile(request.session["auth"].user[0])
  if 'ezidCoOwners' in r:
    d['account_co_owners'] = r['ezidCoOwners']
  else:
    d['account_co_owners'] = ''
  d['recent'] = search.getByOwner(d['user'][0], True, 'updateTime', False, 10, 0)
  d['recent1'] = d['recent'][0:5]
  d['recent2'] = d['recent'][5:10]
  d['field_order'] = FIELD_ORDER
  d['fields_mapped'] = FIELDS_MAPPED
  d['field_defaults'] = FIELD_DEFAULTS
  d['fields_selected'] = [x for x in FIELD_ORDER if x in request.REQUEST ]
  if len(d['fields_selected']) < 1: d['fields_selected'] = FIELD_DEFAULTS
  d['REQUEST'] = request.REQUEST
  d['field_widths'] = FIELD_WIDTHS
  d['field_display_types'] = FIELD_DISPLAY_TYPES
  
  #ensure sorting defaults are set
  if 'order_by' in request.REQUEST and request.REQUEST['order_by'] in d['fields_selected']:
    d['order_by'] = request.REQUEST['order_by']
  else:
    d['order_by'] = [x for x in FIELD_DEFAULT_SORT_PRIORITY if x in d['fields_selected'] ][0]
  if 'sort' in request.REQUEST and request.REQUEST['sort'] in ['asc', 'desc']:
    d['sort'] = request.REQUEST['sort']
  else:
    d['sort'] = 'asc'
    
  #p=page and ps=pagesize -- I couldn't find an auto-paging that uses our type of models and does what we want
  #sorry, had to roll our own
  d['p'] = 1
  d['ps'] = 10
  if 'p' in request.REQUEST and request.REQUEST['p'].isdigit(): d['p'] = int(request.REQUEST['p'])
  if 'ps' in request.REQUEST and request.REQUEST['ps'].isdigit(): d['ps'] = int(request.REQUEST['ps'])
  d['total_results'] = search.getByOwnerCount(d['user'][0], True)
  d['total_pages'] = int(math.ceil(float(d['total_results'])/float(d['ps'])))
  if d['p'] > d['total_pages']: d['p'] = d['total_pages']

  d['results'] = search.getByOwner(d['user'][0], True, d['order_by'], IS_ASCENDING[d['sort']], d['ps'], (d['p']-1)*d['ps'])
  
  return uic.render(request, 'manage/index', d)

def edit(request, identifier):
  d = { 'menu_item' : 'ui_manage.null'}
  d["testPrefixes"] = uic.testPrefixes
  r = ezid.getMetadata(identifier)
  if type(r) is str:
    django.contrib.messages.error(request, uic.formatError(r))
    return redirect("ui_lookup.index")
  if not uic.authorizeUpdate(request, r):
    django.contrib.messages.error(request, "You are not allowed to edit this identifier")
    return redirect("/ezid/id/" + urllib.quote(identifier, ":/"))
  s, m = r
  if uic.identifier_has_block_data(m):
    django.contrib.messages.error(request, "You may not edit this identifier outside of the EZID API")
    return redirect("/ezid/id/" + urllib.quote(identifier, ":/"))
  d['status'] = m['_status'] if '_status' in m else 'public'
  d['export'] = m['_export'] if '_export' in m else 'yes'
  d['post_status'] = d['status']
  d['id_text'] = s.split()[1]
  d['identifier'] = m # identifier object containing metadata
  d['internal_profile'] = metadata.getProfile('internal')
  if request.method == "POST":
    d['post_status'] = request.POST['_status'] if '_status' in request.POST else 'public'
    d['export'] = request.POST['_export'] if '_export' in request.POST else d['export']
    d['current_profile'] = metadata.getProfile(request.POST['current_profile'])
    if request.POST['current_profile'] == request.POST['original_profile']:
      #this means we're saving and going to a save confirmation page
      if uic.validate_simple_metadata_form(request, d['current_profile']):
        to_write = uic.assembleUpdateDictionary(request, d['current_profile'],
          { '_target' : uic.fix_target(request.POST['_target']), '_status': d['post_status'],
            '_export' : ('yes' if (not 'export' in d) or d['export'] == 'yes' else 'no') })
        result = ezid.setMetadata(identifier, uic.user_or_anon_tup(request), uic.group_or_anon_tup(request),
          to_write)
        if result.startswith("success:"):
          django.contrib.messages.success(request, "Identifier updated.")
          return redirect("/ezid/id/" + urllib.quote(identifier, ":/"))
        else:
          d['current_profile'] = metadata.getProfile(m['_profile'])
          d['profiles'] = metadata.getProfiles()[1:]
          django.contrib.messages.error(request, "There was an error updating the metadata for your identifier")
          return uic.render(request, "manage/edit", d)
  elif request.method == "GET":
    if '_profile' in m:
      d['current_profile'] = metadata.getProfile(m['_profile'])
    else:
      d['current_profile'] = metadata.getProfile('dc')
  d['profiles'] = metadata.getProfiles()[1:]
  return uic.render(request, "manage/edit", d)

def _formatErcBlock (block):
  try:
    d = erc.parse(block, concatenateValues=False)
  except erc.ErcParseException:
    return [["error", "Invalid ERC metadata block."]]
  l = []
  # List profile elements first, in profile order.
  for e in metadata.getProfile("erc").elements:
    assert e.name.startswith("erc.")
    n = e.name[4:]
    if n in d:
      for v in d[n]: l.append([n, v])
      del d[n]
  # Now list any remaining elements.
  for k in d:
    for v in d[k]: l.append([k, v])
  return l

def details(request):
  d = { 'menu_item' : 'ui_manage.null'}
  d["testPrefixes"] = uic.testPrefixes
  my_path = "/ezid/id/"
  identifier = request.path[len(my_path):]
  r = ezid.getMetadata(identifier)
  if type(r) is str:
    django.contrib.messages.error(request, uic.formatError(r))
    return redirect("ui_lookup.index")
  d['allow_update'] = uic.authorizeUpdate(request, r)
  s, m = r
  assert s.startswith("success:")
  if not uic.view_authorized_for_identifier(request, m): return redirect("ui_lookup.index")
  d['id_text'] = s.split()[1]
  d['identifier'] = m # identifier object containing metadata
  d['internal_profile'] = metadata.getProfile('internal')
  d['target'] = d['identifier']['_target']
  d['current_profile'] = metadata.getProfile(m['_profile'])
  if d['current_profile'].name == 'erc' and 'erc' in d['identifier']:
    d['erc_block_list'] = _formatErcBlock(d['identifier']['erc'])
  elif d['current_profile'].name == 'datacite' and 'datacite' in d['identifier']:
    r = datacite.dcmsRecordToHtml(d['identifier']["datacite"])
    if r:
      d['datacite_html'] = r
    else:
      d['erc_block_list'] = [["error", "Invalid DataCite metadata record."]]
  d['has_block_data'] = uic.identifier_has_block_data(d['identifier'])
  d['has_resource_type'] = True if (d['current_profile'].name == 'datacite' and 'datacite.resourcetype' in m and m['datacite.resourcetype'] != '') else False
  return uic.render(request, "manage/details", d)
