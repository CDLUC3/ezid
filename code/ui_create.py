import ui_common as uic
from django.shortcuts import redirect
import django.contrib.messages
import metadata
import ezid
import form_objects
import ezidapp.models
import urllib
import re
import datacite_xml
import os.path
import userauth
from django.utils.translation import ugettext as _

"""
    Handles simple and advanced ID creation. If d['id_gen_result'] == 'edit_page'
    user is either about to create an ID, or there is an error condition, 
    (typically field validation) that user is asked to correct.
"""

def _validationErr(action):
  return _("Identifier could not be ") + action +\
    _(" as submitted.  Please check the highlighted fields below for details.")

def index(request):
  d = { 'menu_item' : 'ui_create.index'}
  return redirect("ui_create.simple")

@uic.user_login_required
def simple(request):
  d = { 'menu_item' : 'ui_create.simple' }
  d["testPrefixes"] = uic.testPrefixes
  user = userauth.getUser(request)
  if user.isSuperuser:
    shoulders = [s for s in ezidapp.models.getAllShoulders() if not s.isTest]
  else:
    shoulders = user.shoulders.all()
  d["prefixes"] = sorted([{ "namespace": s.name, "prefix": s.prefix } for\
    s in shoulders],
    key=lambda p: ("%s %s" % (p["namespace"], p["prefix"])).lower())
  if len(d['prefixes']) < 1:
    return uic.render(request, 'create/no_shoulders', d)
  d = simple_form(request, d)
  result = d['id_gen_result']
  if result == 'edit_page':
    return uic.render(request, 'create/simple', d)  # ID Creation page 
  elif result == 'bad_request':
    return uic.badRequest(request)
  elif result.startswith('created_identifier:'):
    return redirect("/id/" + urllib.quote(result.split()[1], ":/"))   # ID Details page

@uic.user_login_required
def advanced(request):
  d = { 'menu_item' :'ui_create.advanced' }
  d["testPrefixes"] = uic.testPrefixes
  user = userauth.getUser(request)
  if user.isSuperuser:
    shoulders = [s for s in ezidapp.models.getAllShoulders() if not s.isTest]
  else:
    shoulders = user.shoulders.all()
  d["prefixes"] = sorted([{ "namespace": s.name, "prefix": s.prefix } for\
    s in shoulders],
    key=lambda p: ("%s %s" % (p["namespace"], p["prefix"])).lower())
  if len(d['prefixes']) < 1:
    return uic.render(request, 'create/no_shoulders', d)
  d = adv_form(request, d)
  result = d['id_gen_result']
  if result == 'edit_page':
    return uic.render(request, 'create/advanced', d)  # ID Creation page 
  elif result == 'bad_request':
    return uic.badRequest(request)
  elif result.startswith('created_identifier:'):
    return redirect("/id/" + urllib.quote(result.split()[1], ":/"))   # ID Details page

def simple_form(request, d):
  """ Create simple identifier code shared by 'Create ID' and 'Demo' pages.
  Takes request and context object, d['prefixes'] should be set before calling.
  Returns dictionary with d['id_gen_result'] of either 'bad_request', 'edit_page' or 
  'created_identifier: <new_id>'. If process is as expected, also includes a form object 
  containing posted data and any related errors. """

  if request.method == "GET":
    REQUEST = request.GET
  elif request.method == "POST":
    REQUEST = request.POST
  else:
    uic.methodNotAllowed(request)
  #selects current_profile based on parameters or profile preferred for prefix type
  d['internal_profile'] = metadata.getProfile('internal')
  if 'current_profile' in REQUEST:
    d['current_profile'] = metadata.getProfile(REQUEST['current_profile'])
    if d['current_profile'] == None:
      d['current_profile'] = metadata.getProfile('erc')
  else:
    if len(d['prefixes']) > 0 and d['prefixes'][0]['prefix'].startswith('doi:'):
      d['current_profile'] = metadata.getProfile('datacite')
    else:
      d['current_profile'] = metadata.getProfile('erc')
      
  if "form_placeholder" not in d: d['form_placeholder'] = None
  if request.method == "GET":
    # Begin ID Creation (empty form)
    
    d['form'] = form_objects.getIdForm(d['current_profile'], d['form_placeholder'], None)
    d['id_gen_result'] = 'edit_page'
  else:
    if "current_profile" not in REQUEST or "shoulder" not in REQUEST:
      d['id_gen_result'] = 'bad_request'
      return d
    d['form'] = form_objects.getIdForm(d['current_profile'], d['form_placeholder'], REQUEST)
    pre_list = [pr['prefix'] for pr in d['prefixes']]
    if not _verifyProperShoulder(request, REQUEST, pre_list): 
      d['id_gen_result'] = 'edit_page'
      return d
    if d['form'].is_valid():
      d = _createSimpleId(d, request, REQUEST)
    else:
      django.contrib.messages.error(request, _validationErr(_("created")))
      d['id_gen_result'] = 'edit_page'
  return d

def adv_form(request, d):
  """ Like simple_form. Takes request and context object. d['prefixes'] should be set 
      before calling.  Includes addtn'l features: 
        custom remainder - optional
        manual_profile - If true, use custom Datacite XML template
        profile_names  - User can choose from different profiles
  """

  d['remainder_box_default'] = form_objects.REMAINDER_BOX_DEFAULT
  #selects current_profile based on parameters or profile preferred for prefix type
  d['manual_profile'] = False
  choice_is_doi = False 
  if request.method == "GET":
    REQUEST = request.GET
  elif request.method == "POST":
    REQUEST = request.POST
  else:
    uic.methodNotAllowed(request)
  if (('shoulder' in REQUEST and REQUEST['shoulder'].startswith("doi:")) \
    or (len(d['prefixes']) > 0 and d['prefixes'][0]['prefix'].startswith('doi:'))):
      choice_is_doi = True 
  if 'current_profile' in REQUEST:
    if REQUEST['current_profile'] in uic.manual_profiles:
      d = _engage_datacite_xml_profile(request, d, 'datacite_xml')
    else: 
      d['current_profile'] = metadata.getProfile(REQUEST['current_profile'])
      if d['current_profile'] == None:
        d['current_profile'] = metadata.getProfile('erc')
  else:
    if choice_is_doi == True:
      d = _engage_datacite_xml_profile(request, d, 'datacite_xml')
    else:
      d['current_profile'] = metadata.getProfile('erc')
  if d['manual_profile'] == False:
    d['current_profile_name'] = d['current_profile'].name
  d['internal_profile'] = metadata.getProfile('internal')
  d['profiles'] = [p for p in metadata.getProfiles()[1:] if p.editable]
  profs = [(p.name, p.displayName, ) for p in d['profiles']] + uic.manual_profiles.items()
  d['profile_names'] = sorted(profs, key=lambda p: p[1].lower())
  # 'datacite_xml' used for advanced profile instead of 'datacite'
  d['profile_names'].remove(('datacite','DataCite'))
  # [TODO: Enhance advanced DOI ERC profile to allow for elements ERC + datacite.publisher or 
  #    ERC + dc.publisher.] For now, just hide this profile. 
  if choice_is_doi: 
    d['profile_names'].remove(('erc','ERC'))

  if request.method == "GET":
    # Begin ID Creation (empty form)
    if d['current_profile_name'] == 'datacite_xml':
      d['form'] = form_objects.getIdForm_datacite_xml()
    else:
      d['form'] = form_objects.getAdvancedIdForm(d['current_profile'], request) 
    d['id_gen_result'] = 'edit_page' 
  else:     # request.method == "POST"
    P = REQUEST
    pre_list = [p['prefix'] for p in d['prefixes'] + d['testPrefixes']]
    if not _verifyProperShoulder(request, P, pre_list): 
      d['id_gen_result'] = 'edit_page'
      return d
    if d['current_profile_name'] == 'datacite_xml':
      d = validate_adv_form_datacite_xml(request, d)
      if 'id_gen_result' in d: return d
      d = _createAdvancedId(d, request, P)
    else:
      if "current_profile" not in P or "shoulder" not in P: 
        d['id_gen_result'] = 'bad_request'
        return d
      d['form'] = form_objects.getAdvancedIdForm(d['current_profile'], request)
      if not (d['form']['form'].is_valid() and d['form']['remainder_form'].is_valid()):
        django.contrib.messages.error(request, _validationErr(_("created")))
        d['id_gen_result'] = 'edit_page'
      else:
        d = _createAdvancedId(d, request, P)
  return d 

def _engage_datacite_xml_profile(request, d, profile_name):
  # Hack: For now, this is the only manual profile
  d['current_profile'] = metadata.getProfile('datacite')
  d['manual_profile'] = True
  d['current_profile_name'] = profile_name
  d['manual_template'] = 'create/_' + d['current_profile_name'] + '.html'
  return d

def validate_adv_form_datacite_xml(request, d):
  """ Creates/validates datacite advanced (xml) form object using request.POST
      from both create/demo and edit areas
      Either sets d['id_gen_result'] = 'edit_page', (due to validation issue)
      or successfully generates XML (sets d['generated_xml'])
  """
  P = request.POST
  assert P is not None
  if (P['action'] == 'create'):
    action_result = _("created")
    identifier = None
  else:   # action='edit'
    action_result = _("modified")
    if not P['identifier']:
      django.contrib.messages.error(request, _("Unable to edit. Identifier not supplied."))
      d['id_gen_result'] = 'edit_page'
      return d
    identifier = P['identifier']
  d['form'] = form_objects.getIdForm_datacite_xml(None, request)
  if not form_objects.isValidDataciteXmlForm(d['form']):
    django.contrib.messages.error(request, _validationErr(action_result))
    d['accordions_open'] = 'open'
    d['id_gen_result'] = 'edit_page'
  else:
    # Testing:
    # d['generated_xml'] = datacite_xml.temp_mock()
    d['generated_xml'] = datacite_xml.formElementsToDataciteXml(
      P.dict(), (P['shoulder'] if 'shoulder' in P else None), identifier)
  return d
 
def _createSimpleId (d, request, P):
  s = ezid.mintIdentifier(request.POST['shoulder'],
    userauth.getUser(request, returnAnonymous=True),
    uic.assembleUpdateDictionary(request, d['current_profile'],
      { '_target' : P['target'], '_export': 'yes' }))
  if s.startswith("success:"):
    new_id = s.split()[1]
    django.contrib.messages.success(request, _("Identifier Created."))
    d['id_gen_result'] = "created_identifier: "+new_id
  else:
    err = _("Identifier could not be created as submitted") + ": "  + s
    django.contrib.messages.error(request, err)
    d['id_gen_result'] = 'edit_page'
  return d

def _createAdvancedId (d, request, P):
  """ Like _createSimpleId, but also checks for elements on advanced create page:
      _status and _export variables; Adds datacite_xml if present. If no remainder 
      is supplied, simply mints an ID                                         """
  # ToDo: Clean this up
  if d['current_profile'].name == 'datacite' and 'generated_xml' in d:
    to_write = { "_profile": 'datacite', '_target' : P['target'], 
      "_status": ("public" if P["publish"] == "True" else "reserved"),
      "_export": ("yes" if P["export"] == "yes" else "no"),
      "datacite": d['generated_xml'] }
  else:
    to_write = uic.assembleUpdateDictionary(request, d['current_profile'],
      { '_target' : P['target'],
      "_status": ("public" if P["publish"] == "True" else "reserved"),
      "_export": ("yes" if P["export"] == "yes" else "no") } )
  if P['remainder'] == '' or P['remainder'] == form_objects.REMAINDER_BOX_DEFAULT:
    s = ezid.mintIdentifier(P['shoulder'],
      userauth.getUser(request, returnAnonymous=True), to_write)
  else:
    s = ezid.createIdentifier(P['shoulder'] + P['remainder'],
      userauth.getUser(request, returnAnonymous=True), to_write)
  if s.startswith("success:"):
    new_id = s.split()[1]
    django.contrib.messages.success(request, _("Identifier Created."))
    d['id_gen_result'] = 'created_identifier: ' + new_id
  else:
    if "-" in s:
      err_msg = re.search(r'^error: .+?- (.+)$', s).group(1)
    else:
      err_msg = re.search(r'^error: (.+)$', s).group(1)
    django.contrib.messages.error(request, _("There was an error creating your identifier") +\
      ": " + err_msg)
    d['accordions_open'] = 'open'
    d['id_gen_result'] = 'edit_page'
  return d

def _verifyProperShoulder (request, P, pre_list):
  if P['shoulder'] not in pre_list:
    django.contrib.messages.error(request, 
      _("Unauthorized to create with this identifier prefix") + ": " + P['shoulder'])
    return False
  return True
