import ui_common as uic
from django.shortcuts import render_to_response, redirect
import django.contrib.messages
import metadata
import ezid

d = { 'menu_item' : 'ui_create.null'}

def index(request):
  return redirect("ui_create.simple")
  d['menu_item'] = 'ui_create.index'
  return uic.render(request, 'create/index', d)

def simple(request):
  if "auth" not in request.session:
    django.contrib.messages.error(request, "Unauthorized.")
    return redirect("ui_home.index")
  d['menu_item'] = 'ui_create.simple'
  d['current_profile'] = metadata.getProfile('dc') #default profile
  d['internal_profile'] = metadata.getProfile('internal')
  if request.method == "POST":
    if "current_profile" not in request.POST or "shoulder" not in request.POST: uic.badRequest()
    d['current_profile'] = metadata.getProfile(request.POST['current_profile'])
    pre_list = [p['prefix'] for p in request.session['prefixes']]
    if request.POST['shoulder'] not in pre_list:
      django.contrib.messages.error(request, "Unauthorized to create with this identifier prefix.")
      return uic.render(request, "create/simple", d)
    write_elements = [e.name for e in d['current_profile'].elements if (e.name in request.POST and request.POST[e.name])] + ["_target"]
    
    #any further validation before this.  If it gets past this line then the data is valid to write
    #where to create id and write elements
    s = ezid.mintIdentifier(request.POST['shoulder'], request.session["auth"].user,
        request.session["auth"].group)
    if s.startswith("success:"):
      new_id = s.split()[1]
    else:
      pass
    to_write = {}
    for e in write_elements:
      to_write[e] = request.POST[e]
    to_write['_profile'] = request.POST['current_profile']
    s = ezid.setMetadata(new_id, request.session["auth"].user, request.session["auth"].group, to_write)
    if s.startswith("success:"):
      django.contrib.messages.success(request, "Identifier created.")
      print s[8:].strip()
      return redirect("ui_lookup.details", s[8:].strip())
    else:
      pass
  return uic.render(request, 'create/simple', d)

def advanced(request):
  d['menu_item'] = 'ui_create.advanced'
  return uic.render(request, 'create/advanced', d)