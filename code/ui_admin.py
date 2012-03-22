import ui_common as uic
import django.contrib.messages
import os
import ezidadmin
import config
import idmap
from django.utils.http import urlencode
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, redirect

def index(request):
  d = { 'menu_item' : 'ui_admin.index'}
  return redirect("ui_admin.usage")
  return uic.render(request, 'admin/index', d)

def usage(request):
  d = { 'menu_item' : 'ui_admin.usage'}
  return uic.render(request, 'admin/usage', d)

def manage_users(request):
  d = { 'menu_item' : 'ui_admin.manage_users' }
  if "auth" not in request.session or request.session["auth"].user[0] != uic.adminUsername:
    return uic.unauthorized()
  d['users'] = ezidadmin.getUsers()
  d['users'].sort(key=lambda i: i['uid'].lower())
  users_by_dn = dict(zip([ x['dn'] for x in d['users']], d['users']))
  if 'user' in request.REQUEST and request.REQUEST['user'] in users_by_dn:
    d['user'] = users_by_dn[request.REQUEST['user']]
  else:
    d['user'] = d['users'][0]
  d['group'] = idmap.getGroupId(d['user']['groupGid'])
    
  return uic.render(request, 'admin/manage_users', d)

def add_group(request):
  if "auth" not in request.session or request.session["auth"].user[0] != uic.adminUsername:
    return uic.unauthorized()
  if request.method != "POST" or not 'grouphandle' in request.POST:
    uic.badRequest()
  P = request.POST
  #print request.POST['grouphandle']
  #successredir = reverse("ui_admin.manage_groups")  + "?" + urlencode({'group': P['grouphandle']})
  #print successredir
  r = ezidadmin.makeLdapGroup(P["grouphandle"].strip())
  if type(r) is str:
    django.contrib.messages.error(request, r)
    return redirect("ui_admin.manage_groups")
  dn = r[0]
  r = ezidadmin.makeGroup(dn, P["grouphandle"].strip(), False, "NONE",
         request.session["auth"].user, request.session["auth"].group)
  if type(r) is str:
    django.contrib.messages.error(request, r)
    return redirect("ui_admin.manage_groups")
  else:
    django.contrib.messages.success(request, "Group successfully created.")
    success_url = reverse("ui_admin.manage_groups") + "?" + urlencode({'group': dn})
    return redirect(success_url)

def manage_groups(request):
  if "auth" not in request.session or request.session["auth"].user[0] != uic.adminUsername:
    return uic.unauthorized()
  d = { 'menu_item' : 'ui_admin.manage_groups' }
  
  # load group information
  d['groups'] = ezidadmin.getGroups()
  d['groups'].sort(key=lambda i: i['gid'].lower())
  groups_by_dn = dict(zip([ x['dn'] for x in d['groups']], d['groups']))
  
  #get current group
  if len(d['groups']) > 0:
    if 'group' in request.REQUEST:
      if request.REQUEST['group'] in groups_by_dn:
        d['group'] = groups_by_dn[request.REQUEST['group']]
      else:
        d['group'] = d['groups'][0]
    else:
      d['group'] = d['groups'][0]
  
  # the section for saving
  if request.method == "POST" and request.POST['group'] == request.POST['original_group']:
    validated = True
    P = request.POST
    if "group" not in P or "description" not in P or\
        "shoulderList" not in P:
        return uic.badRequest()
    d['group']['description'] = request.POST['description']
    if 'agreementOnFile' in request.POST and request.POST['agreementOnFile'] == 'True':
      d['group']['agreementOnFile'] = True
    else:
      d['group']['agreementOnFile'] = False
    sels = request.POST.getlist('shoulderList')
    if '-' in sels:
      sels.remove('-')
    if len(sels) < 1:
      validated = False
      django.contrib.messages.error(request, "You must select at least one shoulder from the shoulder list (or choose NONE).")
    if len(sels) > 1 and ('*' in sels or 'NONE' in sels):
      validated = False
      django.contrib.messages.error(request, "If you select * or NONE you may not select other items in the shoulder list.")
    if validated:
      grp = d['group']
      r = ezidadmin.updateGroup(grp["dn"], grp["description"].strip(),
        grp["agreementOnFile"], ",".join(sels),
        request.session["auth"].user, request.session["auth"].group)
      if type(r) is str:
        django.contrib.messages.error(request, r)
      else:
        django.contrib.messages.success(request, "Successfully updated group")
  else:
    sels = d['group']['shoulderList'].split(",")
  d['selected_shoulders'], d['deselected_shoulders'] = select_shoulder_lists(sels)
  return uic.render(request, 'admin/manage_groups', d)

def system_status(request):
  if "auth" not in request.session or request.session["auth"].user[0] != uic.adminUsername:
    return uic.unauthorized()
  d = { 'menu_item' :  'ui_admin.system_status' }
  d['status_list'] = ezidadmin.systemStatus(None)
  d['js_ids'] =  '[' + ','.join(["'" + x['id'] + "'" for x in d['status_list']]) + ']'
  if request.method == "POST":
    config.load()
    request.session.flush()
    django.contrib.messages.success(request, "EZID reloaded.")
    django.contrib.messages.success(request, "You have been logged out.")
    return uic.redirect("/ezid/")
  return uic.render(request, 'admin/system_status', d)

def ajax_system_status(request):
  if "auth" not in request.session or request.session["auth"].user[0] != uic.adminUsername:
    return uic.unauthorized()
  if request.method != "GET": return uic.methodNotAllowed()
  if "id" in request.GET:
    return uic.plainTextResponse(request.GET["id"] + ":" + ezidadmin.systemStatus(request.GET["id"]))

def alert_message(request):
  if "auth" not in request.session or request.session["auth"].user[0] != uic.adminUsername:
    return uic.unauthorized()
  d = { 'menu_item' : 'ui_admin.alert_message' }
  print 'uic.alertMessage=' + uic.alertMessage
  if request.method == "POST":
    if 'remove_it' in request.POST and request.POST['remove_it'] == 'remove_it':
      if os.path.exists(os.path.join(django.conf.settings.SITE_ROOT, "db","alert_message")):
        os.remove(os.path.join(django.conf.settings.SITE_ROOT, "db",
                               "alert_message"))
      #global alertMessage  
      uic.alertMessage = ''
      django.contrib.messages.success(request, "Message removed.")
    elif 'message' in request.POST:
      m = request.POST["message"].strip()
      f = open(os.path.join(django.conf.settings.SITE_ROOT, "db",
        "alert_message"), "w")
      f.write(m)
      f.close()
      #global alertMessage
      uic.alertMessage = m
      django.contrib.messages.success(request, "Message updated.")
  return uic.render(request, 'admin/alert_message', d)

def select_shoulder_lists(selected_val_list):
  """Makes list of selected and deselected shoulders in format [value, friendly label]
  and returns (selected_list, deselected_list)"""
  #make lists of selected and deselected shoulders
  sorted_shoulders = sorted(uic.shoulders, key=lambda s: s['name'].lower())
  selected_shoulders = []
  deselected_shoulders = []
  selected_labels = [x.strip() for x in selected_val_list]
  for x in ['*', 'NONE']:
    if x in selected_labels:
      selected_shoulders.append([x, x])
    else:
      deselected_shoulders.append([x, x])
  deselected_shoulders.insert(0, ['-', ''])
  
  for x in sorted_shoulders:
    if x['label'] in selected_labels:
      selected_shoulders.append([x['label'], x['name'] + " (" + x['prefix'] + ")"])
    else:
      deselected_shoulders.append([x['label'], x['name'] + " (" + x['prefix'] + ")"])
  return (selected_shoulders, deselected_shoulders)