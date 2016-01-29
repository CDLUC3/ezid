import ui_common as uic
import django.contrib.messages
import ui_search
import ui_create
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
import ezid
import metadata
import math
import useradmin
import erc
import datacite
import datacite_xml
import form_objects
import urllib
import time
import os.path
from lxml import etree, objectify
import re
import ezidapp.models
from django.utils.translation import ugettext as _

FORM_VALIDATION_ERROR_ON_LOAD = _("One or more fields do not validate.  Please check \
  the highlighted fields below for details.")

@uic.user_login_required
def index(request):
  d = { 'menu_item' : 'ui_manage.index' }
  if request.method == "GET":
    d['form'] = form_objects.ManageSearchIdForm() # Build an empty form
    noConstraintsReqd =True 
  elif request.method == "POST":
    d['form'] = form_objects.ManageSearchIdForm(request.POST)
    noConstraintsReqd = False
  d = ui_search.searchIdentifiers(d, request, noConstraintsReqd)
  return uic.render(request, 'manage/index', d)

def _getLatestMetadata(identifier, request):
  """
  The successful return is a pair (status, dictionary) where 'status' is a 
  string that includes the canonical, qualified form of the identifier, as in:
    success: doi:10.5060/FOO
  and 'dictionary' contains element (name, value) pairs.
  """
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
  # ToDo: Remove old technique for presenting Datacite XML in a form
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

    # ToDo: Sort out whether we're editing advanced DataCite or something else
    # ui_create.post_adv_form_datacite_xml(request, d):



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
      form_coll = datacite_xml.dataciteXmlToFormElements(d['identifier']['datacite']) 
      # This is the only item from internal profile that needs inclusion in django form framework
      form_coll.nonRepeating['target'] = id_metadata['_target']
      d['form']=form_objects.getIdForm_datacite_xml(form_coll, request) 
    else:
      if "form_placeholder" not in d: d['form_placeholder'] = None
      d['form'] = form_objects.getIdForm(d['current_profile'], d['form_placeholder'], id_metadata)
      if not d['form'].is_valid():
        django.contrib.messages.error(request, FORM_VALIDATION_ERROR_ON_LOAD)
  return uic.render(request, "manage/edit", d)

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
  if d['current_profile'].name == 'datacite' and 'datacite' in id_metadata:
    r = datacite.dcmsRecordToHtml(id_metadata["datacite"])
    if r:
      d['datacite_html'] = r
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
