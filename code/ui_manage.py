import ui_common as uic
import django.contrib.messages
import ui_search
import ui_create
import download as ezid_download
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
import django.db.models
import ezid
import metadata
import math
import policy
import userauth
import erc
import datacite
import datacite_xml
import form_objects
import urllib
import time
import os.path
import ezidapp.models
from django.utils.translation import ugettext as _

FORM_VALIDATION_ERROR_ON_LOAD = _("One or more fields do not validate.  ") +\
  _("Please check the highlighted fields below for details.")

@uic.user_login_required
def index(request):
  """ Manage Page, listing all Ids owned by user, or if groupadmin, all group users """
  d = { 'menu_item' : 'ui_manage.index' }
  user = userauth.getUser(request)
  if request.method == "GET":
    if not('owner_selected' in request.GET) or request.GET['owner_selected'] == '':
      d['owner_selected'] =  _defaultUser(user)
    else:
      d['owner_selected'] =  request.GET['owner_selected']
    d['queries'] = ui_search.queryDict(request)
    # And preserve query in form object
    d['form'] = form_objects.ManageSearchIdForm(d['queries'])
    d['order_by'] = 'c_update_time'
    d['sort'] = 'asc'
    noConstraintsReqd =True 
  elif request.method == "POST":
    d['owner_selected'] = request.POST['owner_selected'] if 'owner_selected' != '' \
      else _defaultUser(user)
    d['filtered'] = True 
    d['form'] = form_objects.ManageSearchIdForm(request.POST)
    noConstraintsReqd = False
  d['owner_names'] = uic.owner_names(user, "manage")
  d = ui_search.search(d, request, noConstraintsReqd, "manage")
  if not d['form'].has_changed():
    d['filtered'] = False
  return uic.render(request, 'manage/index', d)

def _defaultUser(user):
  """ Pick current user """
  # ToDo: Make sure this works for Realm Admin and picking Groups
  return 'all' if user.isSuperuser else "group_" + user.group.groupname \
    if user.isGroupAdministrator else "user_" + user.username

def _getLatestMetadata(identifier, request):
  """
  The successful return is a pair (status, dictionary) where 'status' is a 
  string that includes the canonical, qualified form of the identifier, as in:
    success: doi:10.5060/FOO
  and 'dictionary' contains element (name, value) pairs.
  """
  return ezid.getMetadata(identifier,
    userauth.getUser(request, returnAnonymous=True))

def _updateEzid(request, d, stts, m_to_upgrade=None):
  """
  Takes data from form fields in /manage/edit and applies them to IDs metadata
  If m_to_upgrade is specified, converts record to advanced datacite 
  Returns ezid.setMetadata (successful return is the identifier string)
  Also removes tags related to old profile if converting to advanced datacite
  """
  m_dict = { '_target' : request.POST['target'], '_status': stts,
      '_export' : ('yes' if (not 'export' in d) or d['export'] == 'yes' else 'no')}
  if m_to_upgrade: 
    d['current_profile'] = metadata.getProfile('datacite')
    # datacite_xml ezid profile is defined by presence of 'datacite' assigned to the 
    # '_profile' key and XML present in the 'datacite' key 
    m_dict['datacite'] = datacite.formRecord(d['id_text'], m_to_upgrade, True)
    m_dict['_profile'] = 'datacite' 
    # Old tag cleanup
    if m_to_upgrade.get("_profile", "") == "datacite": 
      m_dict['datacite.creator'] = ''; m_dict['datacite.publisher'] = '' 
      m_dict['datacite.publicationyear'] = ''; m_dict['datacite.title'] = '' 
      m_dict['datacite.type'] = '' 
    if m_to_upgrade.get("_profile", "") == "dc": 
      m_dict['dc.creator'] = ''; m_dict['dc.date'] = '' 
      m_dict['dc.publisher'] = ''; m_dict['dc.title'] = '' 
      m_dict['dc.type'] = '' 
    if m_to_upgrade.get("_profile", "") == "erc": 
      m_dict['erc.who'] = ''; m_dict['erc.what'] = '' 
      m_dict['erc.when'] = '' 
  # ToDo: Using current_profile here, but isn't this confusing if executing simpleToAdvanced 
  to_write = uic.assembleUpdateDictionary(request, d['current_profile'], m_dict)
  return ezid.setMetadata(d['id_text'],
    userauth.getUser(request, returnAnonymous=True), to_write)

def _alertMessageUpdateError(request, s):
  django.contrib.messages.error(request, 
    _("There was an error updating the metadata for your identifier") + ": " + s)

def _alertMessageUpdateSuccess(request):
  django.contrib.messages.success(request, _("Identifier updated."))

def _assignManualTemplate(d):
  # [TODO: Enhance advanced DOI ERC profile to allow for elements ERC + datacite.publisher or 
  #    ERC + dc.publisher.] For now, just hide this profile. 
  # if d['id_text'].startswith("doi:"):
  #  d['profiles'][:] = [p for p in d['profiles'] if not p.name == 'erc']
  d['manual_profile'] = True
  d['manual_template'] = 'create/_datacite_xml.html'
  return d

def _dataciteXmlToForm(request, d, id_metadata):
  form_coll = datacite_xml.dataciteXmlToFormElements(d['identifier']['datacite']) 
  # Testing
  # xml = datacite_xml.temp_mock()
  # form_coll = datacite_xml.dataciteXmlToFormElements(xml) 
  # This is the only item from internal profile that needs inclusion in django form framework
  form_coll.nonRepeating['target'] = id_metadata['_target']
  d['form']=form_objects.getIdForm_datacite_xml(form_coll, request) 
  return d

def edit(request, identifier):
  """ Edit page for a given ID """
  d = { 'menu_item' : 'ui_manage.null'}
  d["testPrefixes"] = uic.testPrefixes
  r = _getLatestMetadata(identifier, request)
  if type(r) is str:
    django.contrib.messages.error(request, uic.formatError(r))
    return redirect("ui_manage.index")
  s, id_metadata = r 
  if not policy.authorizeUpdate(userauth.getUser(request, returnAnonymous=True), identifier,
    id_metadata["_owner"], id_metadata["_ownergroup"], localNames=True):
    django.contrib.messages.error(request, _("You are not allowed to edit this identifier.  " +\
      "If this ID belongs to you and you'd like to edit, please log in."))
    return redirect("/id/" + urllib.quote(identifier, ":/"))
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
 
  if request.method == "GET": 
    d['is_test_id'] = _isTestId(d['id_text'], d['testPrefixes']) 
    if '_profile' in id_metadata:
      d['current_profile'] = metadata.getProfile(id_metadata['_profile'])
    else:
      d['current_profile'] = metadata.getProfile('dc')
    if d['current_profile'].name == 'datacite' and 'datacite' in id_metadata:
      d = _assignManualTemplate(d)
      d = _dataciteXmlToForm(request, d, id_metadata)
      if not form_objects.isValidDataciteXmlForm(d['form']):
        django.contrib.messages.error(request, FORM_VALIDATION_ERROR_ON_LOAD)
    else:
      if "form_placeholder" not in d: d['form_placeholder'] = None
      d['form'] = form_objects.getIdForm(d['current_profile'], d['form_placeholder'], id_metadata)
      if not d['form'].is_valid():
        django.contrib.messages.error(request, FORM_VALIDATION_ERROR_ON_LOAD)
  else:    # request.method == "POST":
    P = request.POST
    d['pub_status'] = (P['_status'] if '_status' in P else d['pub_status'])
    d['stat_reason'] = (P['stat_reason'] if 'stat_reason' in P else d['stat_reason'])
    d['export'] = P['_export'] if '_export' in P else d['export']
    ''' Profiles could previously be switched in edit template, thus generating
        posibly two differing profiles (current vs original). So we previously did a 
        check here to confirm current_profile equals original profile before saving.''' 
    d['current_profile'] = metadata.getProfile(P['original_profile'])
    if P['_status'] == 'unavailable':
      stts = P['_status'] + " | " + P['stat_reason']
    else:
      stts = P['_status']

    if d['current_profile'].name == 'datacite' and 'datacite' in id_metadata:
      d = _assignManualTemplate(d)
      d = ui_create.validate_adv_form_datacite_xml(request, d)
      if 'id_gen_result' in d:
        return uic.render(request, 'manage/edit', d)  # ID Creation page 
      else:
        assert 'generated_xml' in d
        to_write = { "_profile": 'datacite', '_target' : P['target'],
          "_status": stts, "_export": d['export'], "datacite": d['generated_xml'] }
        s = ezid.setMetadata(P['identifier'], 
          userauth.getUser(request, returnAnonymous=True), to_write)
        if s.startswith("success:"):
          _alertMessageUpdateSuccess(request)
          return redirect("/id/" + urllib.quote(identifier, ":/"))
        else:
          _alertMessageUpdateError(request, s)
    else:
      """ Even if converting from simple to advanced, let's make sure forms validate
          and update identifier first, else don't upgrade.
      """
      d['form'] = form_objects.getIdForm(d['current_profile'], None, P)
      if d['form'].is_valid():
        result = _updateEzid(request, d, stts)
        if not result.startswith("success:"):
          d['current_profile'] = metadata.getProfile(id_metadata['_profile'])
          _alertMessageUpdateError(request, result)
          return uic.render(request, "manage/edit", d)
        else:
          if 'simpleToAdvanced' in P and P['simpleToAdvanced'] == 'True':
            # Convert simple ID to advanced (datacite with XML) 
            result = _updateEzid(request, d, stts, id_metadata)
            r = _getLatestMetadata(identifier, request)
            if type(r) is str:
              django.contrib.messages.error(request, uic.formatError(r))
              return redirect("ui_manage.index")
            s, id_metadata = r 
            if not result.startswith("success:"):
               #  if things fail, just display same simple edit page with error 
              _alertMessageUpdateError(request, result)
            else:
              _alertMessageUpdateSuccess(request)
              return redirect("/id/" + urllib.quote(identifier, ":/"))
          else:
            _alertMessageUpdateSuccess(request)
            return redirect("/id/" + urllib.quote(identifier, ":/"))
  return uic.render(request, "manage/edit", d)

def details(request):
  """ ID Details page for a given ID """
  d = { 'menu_item' : 'ui_manage.null'}
  d["testPrefixes"] = uic.testPrefixes
  my_path = "/id/"
  identifier = request.path_info[len(my_path):]
  r = _getLatestMetadata(identifier, request)
  if type(r) is str:
    django.contrib.messages.error(request, uic.formatError(r))
    return redirect("ui_manage.index")
  s, id_metadata = r
  assert s.startswith("success:")
  d['allow_update'] = policy.authorizeUpdate(userauth.getUser(request, returnAnonymous=True),
    identifier, id_metadata["_owner"], id_metadata["_ownergroup"], localNames=True)
  d['identifier'] = id_metadata 
  d['id_text'] = s.split()[1]
  d['is_test_id'] = _isTestId(d['id_text'], d['testPrefixes']) 
  d['internal_profile'] = metadata.getProfile('internal')
  d['target'] = id_metadata['_target']
  d['current_profile'] = metadata.getProfile(id_metadata['_profile']) or\
    metadata.getProfile('erc')
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
  else:
    return uic.staticTextResponse("No XML metadata.")
  
  # By setting the content type ourselves, we gain control over the
  # character encoding and can properly set the content length.
  ec = content.encode("UTF-8")
  r = django.http.HttpResponse(ec, content_type="application/xml; charset=UTF-8")
  r["Content-Length"] = len(ec)
  return r

def _isTestId(id_text, testPrefixes):
  for pre in testPrefixes:
    if id_text.startswith(pre['prefix']):
      return True
  return False

@uic.user_login_required
def download(request):
  """
  Enqueue a batch download request and display link to user
  """
  d = { 'menu_item' : 'ui_manage.null'}
  q = django.http.QueryDict("format=csv&convertTimestamps=yes&compression=zip", mutable=True)
  q.setlist('column', ["_mappedTitle", "_mappedCreator", "_id", "_owner", "_created", "_updated", "_status"])

  # In case you only want to download IDs based on owner selection:
  # username = uic.getOwnerOrGroup(request.GET['owner_selected'])
  # q['owner'] = ezidapp.models.StoreUser.objects.get(name=username)
  user = userauth.getUser(request)
  q['notify'] = d['mail'] = user.accountEmail
  if user.isRealmAdministrator: q['ownergroup'] = user.realm.groups.all()
  elif user.isGroupAdministrator: q['ownergroup'] = user.group 
  else: q['owner'] = user 
  s = ezid_download.enqueueRequest(user, q)
  if not s.startswith("success:"):
    django.contrib.messages.error(request, s)
    return redirect("ui_manage.index")
  else:
    d['link'] = s.split()[1]
  return uic.render(request, "manage/download", d)

def download_error(request):
  """
  Download link error
  """
  #. Translators: Copy HTML tags over and only translate words outside of these tags
  #. i.e.: <a class="don't_translate_class_names" href="don't_translate_urls">Translate this text</a>
  content = [_("If you have recently requested a batch download of your identifiers, ") +\
    _("the file may not be complete. Please close this window, then try the download ") +\
    _("link again in a few minutes."),
    _("If you are trying to download a file of identifiers from a link that was ") +\
    _("generated over seven days ago, the download link has expired. Go to ") +\
    "<a class='link__primary' href='/manage'>" +\
    _("Manage IDs") + "</a> " +\
    _("and click &quot;Download All&quot; to generate a new download link."),
    _("Please <a class='link__primary' href='/contact'>contact us</a> if you need ") +\
    _("assistance.")]
  return uic.error(request, 404, content)
