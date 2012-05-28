import ui_common as uic
import django.contrib.messages
import os
import ezidadmin
import config
import idmap
import re
import useradmin
from django.utils.http import urlencode
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, redirect

@uic.admin_login_required
def index(request, ssl=False):
  d = { 'menu_item' : 'ui_admin.index'}
  return redirect("ui_admin.usage")
  return uic.render(request, 'admin/index', d)

@uic.admin_login_required
def usage(request, ssl=False):
  d = { 'menu_item' : 'ui_admin.usage'}
  return uic.render(request, 'admin/usage', d)

@uic.admin_login_required
def add_user(request, ssl=False):
  if request.method != "POST" or not 'nu_uid' in request.POST \
      or not 'nu_group' in request.POST:
    uic.badRequest()
  P = request.POST
  uid = P['nu_uid'].strip()
  if uid == '':
    django.contrib.messages.error(request, 'You must enter a username or choose one to add a new user')
    return redirect("ui_admin.manage_users")

  if P['nu_user_status'] == 'new_user':
    try:
      r = idmap.getUserId(uid)
      if r != '':
        django.contrib.messages.error(request, 'The new user you are trying to add already exists.')
        return redirect("ui_admin.manage_users") 
    except AssertionError:
      pass
    r = ezidadmin.makeLdapUser(uid)
    if type(r) is str:
      django.contrib.messages.error(request, r)
      return redirect("ui_admin.manage_users")
  r = ezidadmin.makeUser(uid, P["nu_group"], request.session["auth"].user, request.session["auth"].group)   
  if type(r) is str:
    django.contrib.messages.error(request, r)
    return redirect("ui_admin.manage_users")
  else:
    django.contrib.messages.success(request, "User successfully created")
    success_url = reverse("ui_admin.manage_users") + "?" + urlencode({'user': r[0]})
    return redirect(success_url)

@uic.admin_login_required
def manage_users(request, ssl=False):
  d = { 'menu_item' : 'ui_admin.manage_users' }
  d['users'] = ezidadmin.getUsers()
  d['users'].sort(key=lambda i: i['uid'].lower())
  users_by_dn = dict(zip([ x['dn'] for x in d['users']], d['users']))
  if 'user' in request.REQUEST and request.REQUEST['user'] in users_by_dn:
    d['user'] = users_by_dn[request.REQUEST['user']]
  else:
    d['user'] = d['users'][0]
  if d['user']['sn'] == 'please supply':
    d['user']['sn'] = ''
  if d['user']['mail'] == 'please supply':
    d['user']['mail'] = ''
  
  d['groups'] = ezidadmin.getGroups()
  d['groups'].sort(key=lambda i: i['gid'].lower())
  d['group'] = idmap.getGroupId(d['user']['groupGid'])
  #now for saving
  if request.method == "POST" and request.POST['user'] == request.POST['original_user']:
    u, p = d['user'], request.POST
    u['givenName'], u['sn'], u['mail'], u['telephoneNumber'], u['description'] = \
      p['givenName'], p['sn'], p['mail'], p['telephoneNumber'], p['description']
    u['ezidCoOwners'] = ','.join([x.strip() for x in p['ezidCoOwners'].strip().split("\n")])
    if validate_edit_user(request, u):
      d['user']['currentlyEnabled'] = update_edit_user(request, u)
    else:
      if 'currentlyEnabled' in request.POST and request.POST['currentlyEnabled'].lower() == 'true':
        d['user']['currentlyEnabled'] = 'true'
      else:
        d['user']['currentlyEnabled'] = 'false'
  d['ezidCoOwners'] = "\n".join([x.strip() for x in d['user']['ezidCoOwners'].split(',')])
  return uic.render(request, 'admin/manage_users', d)

@uic.admin_login_required
def add_group(request, ssl=False):
  if request.method != "POST" or not 'grouphandle' in request.POST:
    uic.badRequest()
  P = request.POST
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

@uic.admin_login_required
def manage_groups(request, ssl=False):
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
    if "group" not in P or "description" not in P:
      validated = False
      django.contrib.messages.error(request, "You must submit a description to save this group.")
      #return uic.badRequest()
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

@uic.admin_login_required
def system_status(request, ssl=False):
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

@uic.admin_login_required
def ajax_system_status(request):
  if request.method != "GET": return uic.methodNotAllowed()
  if "id" in request.GET:
    return uic.plainTextResponse(request.GET["id"] + ":" + ezidadmin.systemStatus(request.GET["id"]))

@uic.admin_login_required
def alert_message(request, ssl=False):
  d = { 'menu_item' : 'ui_admin.alert_message' }
  if request.method == "POST":
    if 'remove_it' in request.POST and request.POST['remove_it'] == 'remove_it':
      if os.path.exists(os.path.join(django.conf.settings.SITE_ROOT, "db","alert_message")):
        os.remove(os.path.join(django.conf.settings.SITE_ROOT, "db",
                               "alert_message"))
      #global alertMessage  
      uic.alertMessage = ''
      request.session['hide_alert'] = False
      django.contrib.messages.success(request, "Message removed.")
    elif 'message' in request.POST:
      m = request.POST["message"].strip()
      f = open(os.path.join(django.conf.settings.SITE_ROOT, "db",
        "alert_message"), "w")
      f.write(m)
      f.close()
      #global alertMessage
      uic.alertMessage = m
      request.session['hide_alert'] = False
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

def validate_edit_user(request, user_obj):
  """validates that the fields required to update a user are set, helper function"""
  valid_form = True
  
  required_fields = {'sn': 'Last name', 'mail': 'Email address'}
  for field in required_fields:
    if user_obj[field].strip() == '':
      django.contrib.messages.error(request, required_fields[field] + " must be filled in.")
      valid_form = False
  
  if not re.match('^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$', user_obj['mail'], re.IGNORECASE):
    django.contrib.messages.error(request, "Please enter a valid email address.")
    valid_form = False
  
  if user_obj['ezidCoOwners'] != '':
    coowners = [co.strip() for co in user_obj['ezidCoOwners'].split(',')]
    for coowner in coowners:
      try:
        idmap.getUserId(coowner)
      except AssertionError:
        django.contrib.messages.error(request, coowner + " is not a correct handle for a co-owner.")
        valid_form = False
  
  if not request.POST['userPassword'].strip() == '':
    if len(request.POST['userPassword'].strip()) < 6:
      django.contrib.messages.error(request, "Please use a password length of at least 6 characters.")
      valid_form = False
  return valid_form

def update_edit_user(request, user_obj):
  """Updates the user based on the request and user_object.
  Returns setting of whether account is currentlyEnabled, helper function"""
  curr_enab_state = user_obj['currentlyEnabled']
  #if it's gotten here it has passed validation
  uid = user_obj['uid']
  di = uic.extract(user_obj, ['givenName', 'sn', 'mail', 'telephoneNumber', \
                              'description']) #, 'currentlyEnabled'])
  r = useradmin.setContactInfo(uid, di)
  if type(r) is str:
    django.contrib.messages.error(request, r)
    return curr_enab_state
  r = useradmin.setAccountProfile(uid, user_obj['ezidCoOwners'])
  if type(r) is str:
    django.contrib.messages.error(request, r)
  else:
    django.contrib.messages.success(request, "The account information has been updated.")
  
  if request.POST['userPassword'].strip() != '':
    r = useradmin.resetPassword(uid, request.POST["userPassword"].strip())
    if type(r) is str:
      django.contrib.messages.error(request, r)
    else:
      curr_enab_state = 'true'
      django.contrib.messages.success(request, "The password has been reset.")

  if 'currentlyEnabled' in request.POST and request.POST['currentlyEnabled'].lower() == 'true':
    form_login_enabled = True
  else:
    form_login_enabled = False
  
  if 'currentlyEnabled' in user_obj and user_obj['currentlyEnabled'].lower() == 'true':
    saved_login_enabled = True
  else:
    saved_login_enabled = False
    
  if form_login_enabled != saved_login_enabled:
    if form_login_enabled == True:
      if len(request.POST['userPassword'].strip()) < 1:
        temp_pwd = uic.random_password(8)
        r = useradmin.resetPassword(uid, request.POST["userPassword"].strip())
        if type(r) is str:
          django.contrib.messages.error(request, r)
        else:
          curr_enab_state = 'true'
          django.contrib.messages.success(request, "The user's acount has been activated and the password set to " + temp_pwd)  
    else:
      r = ezidadmin.disableUser(uid)
      if type(r) is str:
        django.contrib.messages.error(request, r)
      else:
        curr_enab_state = 'false'
        django.contrib.messages.success(request, "User has been disabled from logging in.")
  return curr_enab_state
  
    