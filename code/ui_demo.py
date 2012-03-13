import ui_common as uic
from django.shortcuts import redirect
import django.contrib.messages
import metadata
import ezid

def index(request):
  d = { 'menu_item' : 'ui_demo.index' }
  return redirect("ui_demo.simple")
  return uic.render(request, 'create/index', d)

def simple(request):
  d = { 'menu_item' :'ui_demo.simple' }
  d['current_profile'] = metadata.getProfile('erc') #default profile
  d['internal_profile'] = metadata.getProfile('internal')
  d['prefixes'] = sorted(uic.testPrefixes, key=lambda p: p['prefix'])
  if request.method == "POST":
    if "current_profile" not in request.POST or "shoulder" not in request.POST: uic.badRequest()
    d['current_profile'] = metadata.getProfile(request.POST['current_profile'])
    pre_list = [p['prefix'] for p in uic.testPrefixes]
    if request.POST['shoulder'] not in pre_list:
      django.contrib.messages.error(request, "Unauthorized to create with this identifier prefix.")
      return uic.render(request, "demo/simple", d)
    if uic.validate_simple_metadata_form(request, d['current_profile']):
      s = ezid.mintIdentifier(request.POST['shoulder'], uic.user_or_anon_tup(request),
          uic.group_or_anon_tup(request))
      print s
      if s.startswith("success:"):
        new_id = s.split()[1]
      else:
        django.contrib.messages.error(request, "There was an error creating your identifier:"  + s)
        return uic.render(request, "demo/simple", d)
      result = uic.write_profile_elements_from_form(new_id, request, d['current_profile'],
               {'_profile': request.POST['current_profile'], '_target' : request.POST['_target']})
      if result==True:
        django.contrib.messages.success(request, "Identifier created.")
        return redirect("ui_manage.details", new_id)
      else:
        django.contrib.messages.error(request, "There was an error writing the metadata for your identifier: " + s)
  return uic.render(request, 'demo/simple', d)

def advanced(request):
  d = { 'menu_item' : 'ui_demo.advanced' }
  d['remainder_box_default'] = uic.remainder_box_default
  d['current_profile'] = metadata.getProfile('erc') #default profile
  d['internal_profile'] = metadata.getProfile('internal')
  d['prefixes'] = sorted(uic.testPrefixes, key=lambda p: p['prefix'])
  d['profiles'] = metadata.getProfiles()[1:]
  if request.method == "POST":
    d['current_profile'] = metadata.getProfile(request.POST['current_profile'])
    #this means they're not just changing the profile, but are saving
    if request.POST['current_profile'] == request.POST['original_profile']:
      if "current_profile" not in request.POST or "shoulder" not in request.POST: uic.badRequest()
      pre_list = [p['prefix'] for p in uic.testPrefixes]
      if request.POST['shoulder'] not in pre_list:
        django.contrib.messages.error(request, "Unauthorized to create with this identifier prefix.")
        return uic.render(request, "demo/advanced", d)
      if uic.validate_advanced_metadata_form(request, d['current_profile']):
        if request.POST['remainder'] == '' or request.POST['remainder'] == uic.remainder_box_default:
          s = ezid.mintIdentifier(request.POST['shoulder'], uic.user_or_anon_tup(request), 
              uic.group_or_anon_tup(request), request.POST['_target'], request.POST['publish'] == 'False')
        else:
          s = ezid.createIdentifier(request.POST['shoulder'] + request.POST['remainder'], uic.user_or_anon_tup(request),
            uic.group_or_anon_tup(request), request.POST['_target'], request.POST['publish'] == 'False')
        if s.startswith("success:"):
          new_id = s.split()[1]
        else:
          django.contrib.messages.error(request, "There was an error creating your identifier:"  + s)
          return uic.render(request, "demo/advanced", d)
        
        result = uic.write_profile_elements_from_form(new_id, request, d['current_profile'],
                 {'_profile': request.POST['current_profile']}) 
        if result==True:
          django.contrib.messages.success(request, "Identifier created.")
          return redirect("ui_manage.details", new_id)
        else:
          django.contrib.messages.error(request, "There was an error writing the metadata for your identifier: " + s)
  return uic.render(request, 'demo/advanced', d)