import ui_common as uic
from django.shortcuts import redirect
import django.contrib.messages
import metadata
import ezid
import logging
import urllib
import re
import datacite_xml
import policy
import os.path
from lxml import objectify

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
  r = simple_form_processing(request, d)
  if r == 'bad_request':
    uic.badRequest()
  elif r.startswith('created_identifier:'):
    return redirect("/id/" + urllib.quote(r.split()[1], ":/"))
  else:
    return uic.render(request, 'create/simple', d)

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
  r = advanced_form_processing(request, d)
  if r == 'bad_request':
    uic.badRequest()
  elif r.startswith('created_identifier:'):
    return redirect("/id/" + urllib.quote(r.split()[1], ":/"))
  else:
    return uic.render(request, 'create/advanced', d)

def simple_form_processing(request, d):
  """ common code so that create simple identifier code does not repeat across real and test areas.
  returns either 'bad_request', 'edit_page' or 'created_identifier: <new_id>' for results """

  #selects current_profile based on parameters or profile preferred for prefix type
  if 'current_profile' in request.REQUEST:
    d['current_profile'] = metadata.getProfile(request.REQUEST['current_profile'])
    if d['current_profile'] == None:
      d['current_profile'] = metadata.getProfile('erc')
  else:
    if len(d['prefixes']) > 0 and d['prefixes'][0]['prefix'].startswith('doi:'):
      d['current_profile'] = metadata.getProfile('datacite')
    else:
      d['current_profile'] = metadata.getProfile('erc')
      
  d['internal_profile'] = metadata.getProfile('internal')
  
  if request.method == "POST":
    if "current_profile" not in request.POST or "shoulder" not in request.POST: return "bad_request"
    pre_list = [p['prefix'] for p in d['prefixes']]
    if request.POST['shoulder'] not in pre_list:
      django.contrib.messages.error(request, "Unauthorized to create with this identifier prefix.")
      return "edit_page"
    
    if uic.validate_simple_metadata_form(request, d['current_profile']):
      s = ezid.mintIdentifier(request.POST['shoulder'], uic.user_or_anon_tup(request),
          uic.group_or_anon_tup(request), uic.assembleUpdateDictionary(request, d['current_profile'],
          { '_target' : uic.fix_target(request.POST['_target']),
           '_export': 'yes' }))
      if s.startswith("success:"):
        new_id = s.split()[1]
        django.contrib.messages.success(request, "Identifier created.")
        return "created_identifier: "+new_id
      else:
        django.contrib.messages.error(request, "There was an error creating your identifier:"  + s)
        return "edit_page"
  return 'edit_page'

def advanced_form_processing(request, d):
  """takes request and context object, d['prefixes'] should be set before calling"""
  #sets manual_profile, current_profile, current_profile_name, internal_profile,
  #     profiles, profile_names
  
  #Form set up
  d['remainder_box_default'] = uic.remainder_box_default
  #selects current_profile based on parameters or profile preferred for prefix type
  d['manual_profile'] = False
  if 'current_profile' in request.REQUEST:
    if request.REQUEST['current_profile'] in uic.manual_profiles:
      d['manual_profile'] = True
      d['current_profile_name'] = request.REQUEST['current_profile']
      f = open(os.path.join(
        django.conf.settings.PROJECT_ROOT, "static", "datacite_emptyRecord.xml"))
      obj = objectify.parse(f).getroot()
      f.close()
      if obj:
        d['datacite_obj'] = obj
      else:
        django.contrib.messages.error(request, "Unable to render empty datacite form using "\
          "file: " + er)
      d['manual_template'] = 'create/_' + d['current_profile_name'] + '.html'
      d['current_profile'] = d['current_profile_name']
    else: 
      d['current_profile'] = metadata.getProfile(request.REQUEST['current_profile'])
      if d['current_profile'] == None:
        d['current_profile'] = metadata.getProfile('erc')
  else:
    if len(d['prefixes']) > 0 and d['prefixes'][0]['prefix'].startswith('doi:'):
      d['current_profile'] = metadata.getProfile('datacite')
    else:
      d['current_profile'] = metadata.getProfile('erc')
  if d['manual_profile'] == False:
    d['current_profile_name'] = d['current_profile'].name
  d['internal_profile'] = metadata.getProfile('internal')
  d['profiles'] = metadata.getProfiles()[1:]
  profs = [(p.name, p.displayName, ) for p in d['profiles']] + uic.manual_profiles.items()
  d['profile_names'] = sorted(profs, key=lambda p: p[1].lower())
  d['profile_names'].remove(('datacite', 'DataCite')) #not shown in advanced.
 
  if request.method == "POST":
    if "current_profile" not in request.POST or "shoulder" not in request.POST: return 'bad_request'
    pre_list = [p['prefix'] for p in d['prefixes']]
    if request.POST['shoulder'] not in pre_list:
      django.contrib.messages.error(request, "Unauthorized to create with this identifier prefix.")
      return 'edit_page'
    if uic.validate_advanced_metadata_form(request, d['current_profile']):
      """ # For advanced DOI's, this is handled via _datacite_xml.html
            template by ui_demo.ajax_advanced
          No more manual profiles here for processing.
      """
      to_write = uic.assembleUpdateDictionary(request, d['current_profile'],
        { '_target' : uic.fix_target(request.POST['_target']),
        "_status": ("public" if request.POST["publish"] == "True" else "reserved"),
        "_export": ("yes" if request.POST["export"] == "yes" else "no") } )
      
      #write out ID and metadata (one variation with special remainder, one without)
      if request.POST['remainder'] == '' or request.POST['remainder'] == uic.remainder_box_default:
        s = ezid.mintIdentifier(request.POST['shoulder'], uic.user_or_anon_tup(request), 
            uic.group_or_anon_tup(request), to_write)
      else:
        s = ezid.createIdentifier(request.POST['shoulder'] + request.POST['remainder'], uic.user_or_anon_tup(request),
          uic.group_or_anon_tup(request), to_write)
      if s.startswith("success:"):
        new_id = s.split()[1]
        django.contrib.messages.success(request, "Identifier created.")
        return 'created_identifier: ' + new_id
      else:
        if "-" in s:
          err_msg = re.search(r'^error: .+?- (.+)$', s).group(1)
        else:
          err_msg = re.search(r'^error: (.+)$', s).group(1)
        django.contrib.messages.error(request, "There was an error creating your identifier: "  + err_msg)
        return 'edit_page'
  return 'edit_page'
  
