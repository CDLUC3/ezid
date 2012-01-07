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
    pass
  d['profiles'] = metadata.getProfiles()[1:]
  #print [(mm.name, mm.displayName) for mm in metadata.getProfiles()[1:] ]
  if 'current_profile' in request.REQUEST:
    d['current_profile'] = metadata.getProfile(request.REQUEST['current_profile'])
  elif '_profile' in m:
    d['current_profile'] = metadata.getProfile(m['_profile'])
  else:
    d['current_profile'] = metadata.getProfile('dc')
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