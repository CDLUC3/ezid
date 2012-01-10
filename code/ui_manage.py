import ui_common as uic
import django.contrib.messages
from django.shortcuts import redirect
import ezid
import metadata

d = { 'menu_item' : 'ui_manage.null'}

def index(request):
  d['menu_item'] = 'ui_manage.index'
  return uic.render(request, 'manage/index', d)

def edit(request, identifier):
  if uic.is_logged_in(request) == False: return redirect("ui_account.login")
  r = ezid.getMetadata(identifier)
  if type(r) is str:
    django.contrib.messages.error(request, uic.formatError(r))
    return uic.redirect("ui_lookup.index")
  s, m = r
  if not uic.edit_authorized_for_identifier(request, identifier, m): return redirect("ui_manage.details", identifier)
  d['id_text'] = s[8:].strip()
  d['identifier'] = m # identifier object containing metadata
  d['internal_profile'] = metadata.getProfile('internal')
  if request.method == "POST":
    d['current_profile'] = metadata.getProfile(request.POST['current_profile'])
    if request.POST['current_profile'] == request.POST['original_profile']:
      #this means we're saving and going to a save confirmation page
      # XXX add validation here
      result = uic.write_profile_elements_from_form(identifier, request, d['current_profile'],
               {'_profile': request.POST['current_profile'], '_target' : request.POST['_target']})
      if result:
        django.contrib.messages.success(request, "Identifier updated.")
        return redirect("ui_manage.details", identifier)
      else:
        pass #error saving
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
  s, m = r
  print "details: " + s
  assert s.startswith("success:")
  if not uic.view_authorized_for_identifier(request, m): return redirect("ui_lookup.index")
  d['id_text'] = s[8:].strip()
  d['identifier'] = m # identifier object containing metadata
  d['internal_profile'] = metadata.getProfile('internal')
  if '_profile' in m:
    d['current_profile'] = metadata.getProfile(m['_profile'])
  else:
    d['current_profile'] = metadata.getProfile('dc')
  return uic.render(request, "manage/details", d)