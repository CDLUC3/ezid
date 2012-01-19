import ui_common as uic
from django.shortcuts import redirect
import django.contrib.messages
import metadata
import ezid


d = { 'menu_item' : 'ui_demo.null'}

def index(request):
  return redirect("ui_demo.simple")
  d['menu_item'] = 'ui_demo.index'
  return uic.render(request, 'create/index', d)

def simple(request):
  d['menu_item'] = 'ui_demo.simple'
  d['current_profile'] = metadata.getProfile('dc') #default profile
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
      s = ezid.mintIdentifier(request.POST['shoulder'], uic.user_or_anon(request),
          uic.group_or_anon(request))
      print s
      if s.startswith("success:"):
        new_id = s.split()[1]
      else:
        pass
      result = uic.write_profile_elements_from_form(new_id, request, d['current_profile'],
               {'_profile': request.POST['current_profile'], '_target' : request.POST['_target']})
      if result==True:
        django.contrib.messages.success(request, "Identifier created.")
        return redirect("ui_manage.details", new_id)
      else:
        pass
  return uic.render(request, 'demo/simple', d)

def advanced(request):
  d['menu_item'] = 'ui_demo.advanced'
  return uic.render(request, 'create/advanced', d)