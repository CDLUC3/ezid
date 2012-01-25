import ui_common as uic
import django.contrib.messages
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
import ezid
import metadata

d = { 'menu_item' : 'ui_manage.null'}

def index(request):
  d['menu_item'] = 'ui_manage.index'
  return uic.render(request, 'manage/index', d)

def edit(request, identifier):
  r = ezid.getMetadata(identifier)
  if type(r) is str:
    django.contrib.messages.error(request, uic.formatError(r))
    return uic.redirect("ui_lookup.index")
  if not uic.authorizeUpdate(request, r):
    django.contrib.messages.error(request, "You are not allowed to edit this identifier")
    return redirect("ui_manage.details", identifier)
  s, m = r
  d['status'] = m['_status'] if '_status' in m else 'unavailable'
  d['post_status'] = d['status']
  d['id_text'] = s.split()[1]
  d['identifier'] = m # identifier object containing metadata
  d['internal_profile'] = metadata.getProfile('internal')
  if request.method == "POST":
    d['post_status'] = request.POST['_status'] if '_status' in request.POST else 'public'
    d['current_profile'] = metadata.getProfile(request.POST['current_profile'])
    if request.POST['current_profile'] == request.POST['original_profile']:
      #this means we're saving and going to a save confirmation page
      if uic.validate_simple_metadata_form(request, d['current_profile']):
        result = uic.write_profile_elements_from_form(identifier, request, d['current_profile'],
                 {'_profile': request.POST['current_profile'], '_target' : request.POST['_target'],
                  '_status': d['post_status']})
        if result:
          django.contrib.messages.success(request, "Identifier updated.")
          return redirect("ui_manage.details", identifier)
        else:
          print "Could not save this identifier"
  elif request.method == "GET":
    if '_profile' in m:
      d['current_profile'] = metadata.getProfile(m['_profile'])
    else:
      d['current_profile'] = metadata.getProfile('dc')
  d['profiles'] = metadata.getProfiles()[1:]
  return uic.render(request, "manage/edit", d)

def details(request, identifier):
  r = ezid.getMetadata(identifier)
  if type(r) is str:
    django.contrib.messages.error(request, uic.formatError(r))
    return uic.redirect("ui_lookup.index")
  d['allow_update'] = uic.authorizeUpdate(request, r)
  s, m = r
  assert s.startswith("success:")
  if not uic.view_authorized_for_identifier(request, m): return redirect("ui_lookup.index")
  d['id_text'] = s.split()[1]
  d['identifier'] = m # identifier object containing metadata
  d['internal_profile'] = metadata.getProfile('internal')
  if '_profile' in m:
    d['current_profile'] = metadata.getProfile(m['_profile'])
  else:
    d['current_profile'] = metadata.getProfile('dc')
  return uic.render(request, "manage/details", d)