import ui_common as uic
from django.shortcuts import redirect
import django.contrib.messages
import metadata
import ezid
import form_objects
import logging
import urllib
import re
import datacite_xml
import policy
import os.path
from lxml import etree, objectify
from django.utils.translation import ugettext as _

def index(request):
  d = { 'menu_item' : 'ui_create.index'}
  return redirect("ui_create.simple")

@uic.user_login_required
def simple(request):
  d = { 'menu_item' : 'ui_create.simple' }
  d["testPrefixes"] = uic.testPrefixes
  d['prefixes'] = sorted([{ "namespace": s.name, "prefix": s.key }\
    for s in policy.getShoulders(request.session["auth"].user,
    request.session["auth"].group)],
    key=lambda p: (p['namespace'] + ' ' + p['prefix']).lower())
  if len(d['prefixes']) < 1:
    return uic.render(request, 'create/no_shoulders', d)
  d = simple_form_processing(request, d)
  result = d['id_gen_result']
  if result == 'edit_page':
    return uic.render(request, 'create/simple', d)  # ID Creation page 
  elif result == 'bad_request':
    return uic.badRequest()
  elif result.startswith('created_identifier:'):
    return redirect("/id/" + urllib.quote(result.split()[1], ":/"))   # ID Details page

@uic.user_login_required
def advanced(request):
  d = { 'menu_item' :'ui_create.advanced' }
  d["testPrefixes"] = uic.testPrefixes
  d['prefixes'] = sorted([{ "namespace": s.name, "prefix": s.key }\
    for s in policy.getShoulders(request.session["auth"].user,
    request.session["auth"].group)],
    key=lambda p: (p['namespace'] + ' ' + p['prefix']).lower())
  if len(d['prefixes']) < 1:
    return uic.render(request, 'create/no_shoulders', d)
  d = adv_form(request, d)
  result = d['id_gen_result']
  if result == 'edit_page':
    return uic.render(request, 'create/advanced', d)  # ID Creation page 
  elif result == 'bad_request':
    return uic.badRequest()
  elif result.startswith('created_identifier:'):
    return redirect("/id/" + urllib.quote(result.split()[1], ":/"))   # ID Details page

def simple_form_processing(request, d):
  """ Create simple identifier code shared by real and demo sections.
  Takes request and context object, d['prefixes'] should be set before calling.
  Returns dictionary with d['id_gen_result'] of either 'bad_request', 'edit_page' or 
  'created_identifier: <new_id>'. If process is as expected, also includes a form object 
  containing posted data and any related errors. """

  if request.method == "GET":
    REQUEST = request.GET
  else:
    REQUEST = request.POST
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
    d['form'] = form_objects.getIdForm(d['current_profile'], d['form_placeholder'])
    d['id_gen_result'] = 'edit_page'
  else:
    if "current_profile" not in REQUEST or "shoulder" not in REQUEST:
      d['id_gen_result'] = 'bad_request'
      return d
    d['form'] = form_objects.getIdForm(d['current_profile'], d['form_placeholder'], request)
    pre_list = [pr['prefix'] for pr in d['prefixes']]
    if REQUEST['shoulder'] not in pre_list:
      django.contrib.messages.error(request, _("Unauthorized to create with \
        this identifier prefix") + ": " + REQUEST['shoulder'])
      d['id_gen_result'] = 'edit_page'
      return d
    if d['form'].is_valid():
      s = ezid.mintIdentifier(REQUEST['shoulder'], uic.user_or_anon_tup(request),
          uic.group_or_anon_tup(request), uic.assembleUpdateDictionary(request, d['current_profile'],
          { '_target' : uic.fix_target(REQUEST['_target']),
           '_export': 'yes' }))
      if s.startswith("success:"):
        new_id = s.split()[1]
        django.contrib.messages.success(request, _("IDENTIFIER CREATED."))
        d['id_gen_result'] = "created_identifier: "+new_id
      else:
        django.contrib.messages.error(request, _("Identifier could not be \
          created as submitted") + ": "  + s)
        d['id_gen_result'] = 'edit_page'
    else:
      django.contrib.messages.error(request, _("Identifier could not be \
        created as submitted.  Please check the highlighted fields below \
        for details."))
      d['id_gen_result'] = 'edit_page'
  return d

def adv_form(request, d):
  """Like simple_form_processing. Takes request and context object, d['prefixes'] 
  should be set before calling. Sets manual_profile, current_profile, current_profile_name, 
  internal_profile, profiles, profile_names"""

  d['remainder_box_default'] = form_objects.remainder_box_default
  #selects current_profile based on parameters or profile preferred for prefix type
  d['manual_profile'] = False
  choice_is_doi = False 
  if request.method == "GET":
    REQUEST = request.GET
  else:
    REQUEST = request.POST
  if (('shoulder' in REQUEST and REQUEST['shoulder'].startswith("doi:")) \
    or (len(d['prefixes']) > 0 and d['prefixes'][0]['prefix'].startswith('doi:'))):
      choice_is_doi = True 
  if 'current_profile' in REQUEST:
    if REQUEST['current_profile'] in uic.manual_profiles:
      d = _engage_datacite_xml_profile(request, d, REQUEST['current_profile'])
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
  profs = [(p.name, p.displayName, ) for p in d['profiles']] + \
    uic.manual_profiles.items()
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
      d['form'] = form_objects.getAdvancedIdForm(d['current_profile']) 
    d['id_gen_result'] = 'edit_page' 
  else:     # request.method == "POST"
    P = REQUEST
    if d['current_profile_name'] == 'datacite_xml':
      d = adv_form_datacite_xml(request, d)
    else:
      if "current_profile" not in P or "shoulder" not in P: 
        d['id_gen_result'] = 'bad_request'
        return d
      d['form'] = form_objects.getAdvancedIdForm(d['current_profile'], request)
      pre_list = [p['prefix'] for p in d['prefixes']]
      if P['shoulder'] not in pre_list:
        django.contrib.messages.error(request, _("Unauthorized to create with \
          this identifier prefix: ") + P['shoulder'])
        d['id_gen_result'] = 'edit_page'
        return d
      if not (d['form']['form'].is_valid() and d['form']['remainder_form'].is_valid()):
        django.contrib.messages.error(request, _("Identifier could not be \
          created as submitted. Please check the highlighted fields below for \
          details."))
        d['id_gen_result'] = 'edit_page'
      else:
        to_write = uic.assembleUpdateDictionary(request, d['current_profile'],
          { '_target' : uic.fix_target(P['_target']),
          "_status": ("public" if P["publish"] == "True" else "reserved"),
          "_export": ("yes" if P["export"] == "yes" else "no") } )
      
        #write out ID and metadata (one variation with special remainder, one without)
        if P['remainder'] == '' or P['remainder'] == form_objects.remainder_box_default:
          s = ezid.mintIdentifier(P['shoulder'], uic.user_or_anon_tup(request), 
              uic.group_or_anon_tup(request), to_write)
        else:
          s = ezid.createIdentifier(P['shoulder'] + P['remainder'], 
            uic.user_or_anon_tup(request), uic.group_or_anon_tup(request), to_write)
        if s.startswith("success:"):
          new_id = s.split()[1]
          django.contrib.messages.success(request, _("IDENTIFIER CREATED."))
          d['id_gen_result'] = 'created_identifier: ' + new_id
        else:
          if "-" in s:
            err_msg = re.search(r'^error: .+?- (.+)$', s).group(1)
          else:
            err_msg = re.search(r'^error: (.+)$', s).group(1)
          django.contrib.messages.error(request, _("There was an error creating \
            your identifier") + ": " + err_msg)
          d['id_gen_result'] = 'edit_page'
  return d 

def _engage_datacite_xml_profile(request, d, profile_name):
  d['manual_profile'] = True
  d['current_profile_name'] = profile_name
  ''' Feed in a whole, empty XML record so that elements can be properly
      displayed in form fields on manage/edit page ''' 
  f = open(os.path.join(
    django.conf.settings.PROJECT_ROOT, "static", "datacite_emptyRecord.xml"))
  obj = objectify.parse(f).getroot()
  f.close()
  if obj is not None:
    d['datacite_obj'] = obj
  else:
    django.contrib.messages.error(request, _("Unable to render empty datacite \
      form using file") + ": " + f.name)
  d['manual_template'] = 'create/_' + d['current_profile_name'] + '.html'
  d['current_profile'] = d['current_profile_name']
  return d

def adv_form_datacite_xml(request, d):
  """Takes the request and processes create datacite advanced (xml) form
  from both create/demo and edit areas"""
  error_msgs = []

  P = request.POST
  if (P['action'] == 'create'):
    action_result = [_("creating"), _("created")]
  else:   # action='edit'
    action_result = [_("editing"), _("edited successfully")]
    if not P['identifier']:
      error_msgs.append(_("Unable to edit. Identifier not supplied."))
  d["testPrefixes"] = uic.testPrefixes
  if 'auth' in request.session:
    d['prefixes'] = sorted([{ "namespace": s.name, "prefix": s.key }\
      for s in policy.getShoulders(request.session["auth"].user,
      request.session["auth"].group)],
      key=lambda p: (p['namespace'] + ' ' + p['prefix']).lower())
  else:
    d['prefixes'] = []
  pre_list = [p['prefix'] for p in d['prefixes'] + d['testPrefixes']]
  # import pdb; pdb.set_trace()
  if (P['action'] == 'create' and\
      P['shoulder'] not in pre_list):
      error_msgs.append(_("Unauthorized to create with this identifier \
        prefix."))
  d['form'] = form_objects.getIdForm_datacite_xml(None, request)
  if not (d['form']['remainder_form'].is_valid() and 
    d['form']['title_set'].is_valid() and d['form']['creator_set'].is_valid()):
    d['id_gen_result'] = 'edit_page'
  else:
 
    # ToDo: Come back to this once Django form validation is worked out 
    # return_val = datacite_xml.generate_xml(P)
    # xsd_path = django.conf.settings.PROJECT_ROOT + "/xsd/datacite-kernel-3/metadata.xsd"
    # if datacite_xml.validate_document(return_val, xsd_path, error_msgs) == False:
    #  return uic.jsonResponse({'status': 'failure', 'errors': error_msgs })

    django.contrib.messages.success(request, _("Identifier") + "  " \
      + action_result[1] + ".")
    d['id_gen_result'] = 'created_identifier: ' + 'ark:/85143/c4hp4m'
  return d

  #  if (P['action'] == 'edit'): 
  #    if P['_status'] == 'unavailable':
  #      stts = P['_status'] + " | " + P['stat_reason']
  #    else:
  #      stts = P['_status']
  #    to_write = _assembleMetadata(request, stts, return_val) 
  #    s = ezid.setMetadata(P['identifier'], uic.user_or_anon_tup(request),\
  #        uic.group_or_anon_tup(request), to_write)
  #  else:  # action=='create'
  #    stts = ("public" if P["publish"] == "True" else "reserved")
  #    to_write = _assembleMetadata(request, stts, return_val) 
    
      #write out ID and metadata (one variation with special remainder, one without)
  #    if P['remainder'] == '' or\
  #       P['remainder'] == form_objects.remainder_box_default:
  #      s = ezid.mintIdentifier(P['shoulder'], uic.user_or_anon_tup(request), 
  #        uic.group_or_anon_tup(request), to_write)
  #    else:
  #      s = ezid.createIdentifier(P['shoulder'] +\
  #          P['remainder'], uic.user_or_anon_tup(request),
  #      uic.group_or_anon_tup(request), to_write)

  #  if s.startswith("success:"):
  #    new_id = s.split()[1]
  #    django.contrib.messages.success(request, _("Identifier") + "  " \
  #      + action_result[1] + ".")
  #    d['id_gen_result'] = 'created_identifier: ' + new_id
  #  else:
  #    django.contrib.messages.error(request, _("Identifier could not be \
  #      created as submitted") + ": "  + s)
  #    d['id_gen_result'] = 'edit_page'
  #return d
 
def _assembleMetadata (request, stts, return_val):
    # There is no datacite_xml ezid profile. Just use 'datacite'
    return { "_profile": 'datacite',
      '_target' : uic.fix_target(request.POST['_target']),
      "_status": stts,
      "_export": ("yes" if request.POST.get("export", "no") == "yes" or
                  request.POST.get("_export", "no") == "yes" else "no"),
      "datacite": return_val }
 
