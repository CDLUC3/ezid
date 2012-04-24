import ui_common as uic
from django.shortcuts import redirect
import django.contrib.messages
import metadata
import ezid
import logging

def index(request):
  d = { 'menu_item' : 'ui_create.index'}
  return redirect("ui_create.simple")
  return uic.render(request, 'create/index', d)

def simple(request):
  d = { 'menu_item' : 'ui_create.simple' }
  d["testPrefixes"] = uic.testPrefixes
  if uic.is_logged_in(request) == False: return redirect("ui_account.login")
  d['prefixes'] = sorted(request.session['prefixes'], key=lambda p: p['prefix']) #must be done before calling form processing
  r = simple_form_processing(request, d)
  if r == 'bad_request':
    uic.badRequest()
  elif r.startswith('created_identifier:'):
    return redirect("/ezid/id/" + r.split()[1])
  else:
    return uic.render(request, 'create/simple', d)

def advanced(request):
  d = { 'menu_item' :'ui_create.advanced' }
  d["testPrefixes"] = uic.testPrefixes
  if uic.is_logged_in(request) == False: return redirect("ui_account.login")
  d['prefixes'] = sorted(request.session['prefixes'], key=lambda p: p['prefix']) #must be done before calling form processing
  r = advanced_form_processing(request, d)
  if r == 'bad_request':
    uic.badRequest()
  elif r.startswith('created_identifier:'):
    return redirect("/ezid/id/" + r.split()[1])
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
          uic.group_or_anon_tup(request))
      if s.startswith("success:"):
        new_id = s.split()[1]
      else:
        django.contrib.messages.error(request, "There was an error creating your identifier:"  + s)
        return "edit_page"
      result = uic.write_profile_elements_from_form(new_id, request, d['current_profile'],
               {'_profile': request.POST['current_profile'], '_target' : uic.fix_target(request.POST['_target']) }) 
      if result==True:
        django.contrib.messages.success(request, "Identifier created.")
        return "created_identifier: "+new_id
        #return redirect("/ezid/id/" + new_id)
      else:
        django.contrib.messages.error(request, "There was an error writing the metadata for your identifier: " + s)
        return "edit_page"
  return 'edit_page'

def advanced_form_processing(request, d):
  """takes request and context object, d['prefixes'] should be set before calling"""
  d['remainder_box_default'] = uic.remainder_box_default
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
  d['profiles'] = metadata.getProfiles()[1:]
  if request.method == "POST":
    if "current_profile" not in request.POST or "shoulder" not in request.POST: return 'bad_request'
    pre_list = [p['prefix'] for p in d['prefixes']]
    if request.POST['shoulder'] not in pre_list:
      django.contrib.messages.error(request, "Unauthorized to create with this identifier prefix.")
      return 'edit_page'
    if uic.validate_advanced_metadata_form(request, d['current_profile']):
      if request.POST['remainder'] == '' or request.POST['remainder'] == uic.remainder_box_default:
        s = ezid.mintIdentifier(request.POST['shoulder'], uic.user_or_anon_tup(request), 
            uic.group_or_anon_tup(request), uic.fix_target(request.POST['_target']), request.POST['publish'] == 'False')
      else:
        s = ezid.createIdentifier(request.POST['shoulder'] + request.POST['remainder'], uic.user_or_anon_tup(request),
          uic.group_or_anon_tup(request), uic.fix_target(request.POST['_target']), request.POST['publish'] == 'False')
      if s.startswith("success:"):
        new_id = s.split()[1]
      else:
        django.contrib.messages.error(request, "There was an error creating your identifier:"  + s)
        return 'edit_page'
      result = uic.write_profile_elements_from_form(new_id, request, d['current_profile'],
         {'_profile': request.POST['current_profile'], '_target' : uic.fix_target(request.POST['_target']) })
      if result==True:
        django.contrib.messages.success(request, "Identifier created.")
        return 'created_identifier: ' + new_id
      else:
        django.contrib.messages.error(request, "There was an error writing the metadata for your identifier: " + s)
        return 'edit_page'
  return 'edit_page'