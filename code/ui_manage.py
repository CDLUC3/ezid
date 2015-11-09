import ui_common as uic
import django.contrib.messages
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
import ezid
import metadata
import math
import useradmin
import erc
import datacite
import urllib
import time
import os.path
from lxml import etree, objectify
import re
import ezidapp.models


# these are layout properties for the fields in the manage index page,
# if I had realized there were going to be so many properties up front, I probably would
# have created a field layout object with a number of properties instead.

# The order to display fields both in the customize check boxes and the columns
FIELD_ORDER = ['identifier', 'owner', 'coOwners', 'createTime', 'updateTime', 'status',\
                'mappedTitle', 'mappedCreator']

# The default selected fields for display if custom fields haven't been defined
FIELD_DEFAULTS = ['identifier', 'updateTime', 'mappedTitle', 'mappedCreator']

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

@uic.user_login_required
def index(request):
  if request.method == "GET":
    REQUEST = request.GET
  else:
    REQUEST = request.POST
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
  d['field_order'] = FIELD_ORDER
  d['field_norewrite'] = FIELD_ORDER + ['includeCoowned']
  d['fields_mapped'] = FIELDS_MAPPED
  d['field_defaults'] = FIELD_DEFAULTS
  d['fields_selected'] = [x for x in FIELD_ORDER if x in REQUEST ]
  if len(d['fields_selected']) < 1: d['fields_selected'] = FIELD_DEFAULTS
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
  d['total_results'] = ezidapp.models.SearchIdentifier.objects.\
    filter(owner__username=d['user'][0]).count()
  d['total_pages'] = int(math.ceil(float(d['total_results'])/float(d['ps'])))
  if d['p'] > d['total_pages']: d['p'] = d['total_pages']
  d['p'] = max(d['p'], 1)
  orderColumn = re.sub("mapped", "resource", d['order_by'])
  if not IS_ASCENDING[d['sort']]: orderColumn = "-" + orderColumn
  d['results'] = []
  for id in ezidapp.models.SearchIdentifier.objects.\
    filter(owner__username=d['user'][0]).\
    only("identifier", "owner__username", "createTime", "updateTime",
    "status", "unavailableReason", "resourceTitle", "resourceCreator").\
    select_related("owner__username").\
    order_by(orderColumn)[(d['p']-1)*d['ps']:d['p']*d['ps']]:
    result = { "identifier": id.identifier, "owner": id.owner.username,
      "coOwners": "", "createTime": id.createTime,
      "updateTime": id.updateTime, "status": id.get_status_display(),
      "mappedTitle": id.resourceTitle, "mappedCreator": id.resourceCreator }
    if id.isUnavailable and id.unavailableReason != "":
      result["status"] += " | " + id.unavailableReason
    d['results'].append(result)
  return uic.render(request, 'manage/index', d)

def _getLatestMetadata(identifier, request):
  if "auth" in request.session:
    r = ezid.getMetadata(identifier, request.session["auth"].user,
      request.session["auth"].group)
  else:
    r = ezid.getMetadata(identifier)
  return r

def _updateMetadata(request, d, stts, _id_metadata=None):
  """
  Takes data from form fields in /manage/edit and applies them to IDs metadata
  If _id_metadata is specified, converts record to advanced datacite 
  Returns ezid.setMetadata (successful return is the identifier string)
  Also removes tags related to old profile if converting to advanced datacite
  """
  metadata_dict = { '_target' : uic.fix_target(request.POST['_target']), '_status': stts,
      '_export' : ('yes' if (not 'export' in d) or d['export'] == 'yes' else 'no')}
  if _id_metadata: 
    metadata_dict['datacite'] = datacite.formRecord(d['id_text'], _id_metadata, True)
    metadata_dict['_profile'] = 'datacite' 
    # Old tag cleanup
    if _id_metadata.get("_profile", "") == "datacite": 
      metadata_dict['datacite.creator'] = ''; metadata_dict['datacite.publisher'] = '' 
      metadata_dict['datacite.publicationyear'] = ''; metadata_dict['datacite.title'] = '' 
      metadata_dict['datacite.type'] = '' 
    if _id_metadata.get("_profile", "") == "dc": 
      metadata_dict['dc.creator'] = ''; metadata_dict['dc.date'] = '' 
      metadata_dict['dc.publisher'] = ''; metadata_dict['dc.title'] = '' 
      metadata_dict['dc.type'] = '' 
    if _id_metadata.get("_profile", "") == "erc": 
      metadata_dict['erc.who'] = ''; metadata_dict['erc.what'] = '' 
      metadata_dict['erc.when'] = '' 
  to_write = uic.assembleUpdateDictionary(request, d['current_profile'], metadata_dict)
  return ezid.setMetadata(d['id_text'], uic.user_or_anon_tup(request), 
    uic.group_or_anon_tup(request), to_write)

def _alertMessageUpdateError(request):
  django.contrib.messages.error(request, "There was an error updating the metadata for your identifier")

def _alertMessageUpdateSuccess(request):
  django.contrib.messages.success(request, "Identifier updated.")

def _addDataciteXmlToDict(id_metadata, d):
  # There is no datacite_xml ezid profile. Just use 'datacite'
  # [TODO: Enhance advanced DOI ERC profile to allow for elements ERC + datacite.publisher or 
  #    ERC + dc.publisher.] For now, just hide this profile. 
  if d['id_text'].startswith("doi:"):
    d['profiles'][:] = [p for p in d['profiles'] if not p.name == 'erc']
  datacite_obj = objectify.fromstring(id_metadata["datacite"])
  if datacite_obj is not None:
    d['datacite_obj'] = datacite_obj 
    d['manual_profile'] = True
    d['manual_template'] = 'create/_datacite_xml.html'
    ''' Also feed in a whole, empty XML record so that elements can be properly
        displayed in form fields on manage/edit page ''' 
    f = open(os.path.join(
        django.conf.settings.PROJECT_ROOT, "static", "datacite_emptyRecord.xml"))
    d['datacite_obj_empty'] = objectify.parse(f).getroot()
    f.close()
  else:
    d['erc_block_list'] = [["error", "Invalid DataCite metadata record."]]
  return d

def edit(request, identifier):
  d = { 'menu_item' : 'ui_manage.null'}
  d["testPrefixes"] = uic.testPrefixes
  r = _getLatestMetadata(identifier, request)
  if type(r) is str:
    django.contrib.messages.error(request, uic.formatError(r))
    return redirect("ui_manage.index")
  if not uic.authorizeUpdate(request, r):
    django.contrib.messages.error(request, "You are not allowed to edit this identifier")
    return redirect("/id/" + urllib.quote(identifier, ":/"))
  s, id_metadata = r 
  d['identifier'] = id_metadata 
  t_stat = [x.strip() for x in id_metadata['_status'].split("|", 1)]
  d['pub_status'] = t_stat[0]
  d['orig_status'] = t_stat[0]
  d['stat_reason'] = None
  if t_stat[0] == 'unavailable' and len(t_stat) > 1:
    d['stat_reason'] = t_stat[1]
  d['export'] = id_metadata['_export'] if '_export' in id_metadata else 'yes'
  d['id_text'] = s.split()[1]
  d['internal_profile'] = metadata.getProfile('internal')
  d['profiles'] = metadata.getProfiles()[1:]
  if request.method == "POST":
    # datacite_xml editing uses ui_create.ajax_advanced, so doesn't use this step.
    d['pub_status'] = (request.POST['_status'] if '_status' in request.POST else d['pub_status'])
    d['stat_reason'] = (request.POST['stat_reason'] if 'stat_reason' in request.POST else d['stat_reasons'])
    d['export'] = request.POST['_export'] if '_export' in request.POST else d['export']
    ''' Profiles could previously be switched in edit template, thus generating
        posibly two differing profiles (current vs original). So we previously did a 
        check here to confirm current_profile equals original profile before saving.''' 
    d['current_profile'] = metadata.getProfile(request.POST['original_profile'])
    #this means we're saving and going to a save confirmation page
    if request.POST['_status'] == 'unavailable':
      stts = request.POST['_status'] + " | " + request.POST['stat_reason']
    else:
      stts = request.POST['_status']
    # Even if converting from simple to advanced, let's validate fields first
    if uic.validate_simple_metadata_form(request, d['current_profile']):
      result = _updateMetadata(request, d, stts)
      if not result.startswith("success:"):
        d['current_profile'] = metadata.getProfile(id_metadata['_profile'])
        _alertMessageUpdateError(request)
        return uic.render(request, "manage/edit", d)
      else:
        if 'simpleToAdvanced' in request.POST and request.POST['simpleToAdvanced'] == 'True':
          # simpleToAdvanced button was selected 
          result = _updateMetadata(request, d, stts, id_metadata)
          r = _getLatestMetadata(identifier, request)
          if type(r) is str:
            django.contrib.messages.error(request, uic.formatError(r))
            return redirect("ui_manage.index")
          s, id_metadata = r 
          if not result.startswith("success:"):
            _alertMessageUpdateError(request)
          else:
            d['identifier'] = id_metadata
            d['current_profile'] = metadata.getProfile('datacite')
            d = _addDataciteXmlToDict(id_metadata, d)
            _alertMessageUpdateSuccess(request)
          return uic.render(request, "manage/edit", d)
        else:
          _alertMessageUpdateSuccess(request)
          return redirect("/id/" + urllib.quote(identifier, ":/"))
  elif request.method == "GET": 
    if '_profile' in id_metadata:
      d['current_profile'] = metadata.getProfile(id_metadata['_profile'])
    else:
      d['current_profile'] = metadata.getProfile('dc')
    if d['current_profile'].name == 'datacite' and 'datacite' in id_metadata:
      d = _addDataciteXmlToDict(id_metadata, d)
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
  my_path = "/id/"
  identifier = request.path_info[len(my_path):]
  r = _getLatestMetadata(identifier, request)
  if type(r) is str:
    django.contrib.messages.error(request, uic.formatError(r))
    return redirect("ui_manage.index")
  d['allow_update'] = uic.authorizeUpdate(request, r)
  s, id_metadata = r
  assert s.startswith("success:")
  d['identifier'] = id_metadata 
  d['id_text'] = s.split()[1]
  d['internal_profile'] = metadata.getProfile('internal')
  d['target'] = id_metadata['_target']
  d['current_profile'] = metadata.getProfile(id_metadata['_profile'])
  d['recent_creation'] = identifier.startswith('doi') and \
        (time.time() - float(id_metadata['_created']) < 60 * 30)
  d['recent_update'] = identifier.startswith('doi') and \
        (time.time() - float(id_metadata['_updated']) < 60 * 30)
  if d['current_profile'].name == 'erc' and 'erc' in id_metadata:
    d['erc_block_list'] = _formatErcBlock(id_metadata['erc'])
  elif d['current_profile'].name == 'datacite' and 'datacite' in id_metadata:
    r = datacite.dcmsRecordToHtml(id_metadata["datacite"])
    if r:
      d['datacite_html'] = r
    else:
      d['erc_block_list'] = [["error", "Invalid DataCite metadata record."]]
  if d['current_profile'].name == 'crossref' and 'crossref' in id_metadata and \
    id_metadata['crossref'].strip() != "":
    d['has_crossref_metadata'] = True 
  t_stat = [x.strip() for x in id_metadata['_status'].split("|", 1)]
  d['pub_status'] = t_stat[0]
  if t_stat[0] == 'unavailable' and len(t_stat) > 1:
    d['stat_reason'] = t_stat[1] 
  d['has_block_data'] = uic.identifier_has_block_data(id_metadata)
  d['has_resource_type'] = True if (d['current_profile'].name == 'datacite' \
    and 'datacite.resourcetype' in id_metadata \
    and id_metadata['datacite.resourcetype'] != '') else False
  return uic.render(request, "manage/details", d)

def display_xml(request, identifier):
  """
  Used for displaying DataCite or CrossRef XML
  """
  d = { 'menu_item' : 'ui_manage.null'}
  r = _getLatestMetadata(identifier, request)
  if type(r) is str:
    django.contrib.messages.error(request, uic.formatError(r))
    return redirect("/")
  s, id_metadata = r 
  assert s.startswith("success:")
  d['identifier'] = id_metadata 
  d['current_profile'] = metadata.getProfile(id_metadata['_profile'])
  if d['current_profile'].name == 'datacite' and 'datacite' in id_metadata:
    content = id_metadata["datacite"]
  elif d['current_profile'].name == 'crossref' and 'crossref' in id_metadata:
    content = id_metadata["crossref"]
  
  # By setting the content type ourselves, we gain control over the
  # character encoding and can properly set the content length.
  ec = content.encode("UTF-8")
  r = django.http.HttpResponse(ec, content_type="application/xml; charset=UTF-8")
  r["Content-Length"] = len(ec)
  return r
