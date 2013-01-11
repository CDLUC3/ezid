import ui_common as uic
import django.contrib.messages
import os
import ezidadmin
import config
import idmap
import re
import useradmin
import stats
import datetime
import anvl
from django.utils.http import urlencode
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, redirect
from django import forms
from collections import *


@uic.admin_login_required
def index(request, ssl=False):
  d = { 'menu_item' : 'ui_admin.index'}
  #return redirect("ui_admin.usage")
  return uic.render(request, 'admin/index', d)

@uic.admin_login_required
def usage(request, ssl=False):
  d = { 'menu_item' : 'ui_admin.usage'}
  #make select list choices
  users = ezidadmin.getUsers()
  users.sort(key=lambda i: i['uid'].lower())
  groups = ezidadmin.getGroups()
  groups.sort(key=lambda i: i['gid'].lower())
  user_choices = [("user_" + x['arkId'], x['uid']) for x in users]
  group_choices = [("group_" + x['arkId'], x['gid']) for x in groups]
  d['choices'] = [("all", "All EZID")] + [('',''), ('', '-- Groups --')] + \
      group_choices + [('',''), ('', '-- Users --')] + user_choices
      
  if request.method != "POST" or not('choice' in request.POST) or request.POST['choice'] == '':
    d['choice'] = 'all'
  else:
    d['choice'] = request.POST['choice']
    
  #query all
  user_id, group_id = None, None
  if d['choice'].startswith('user_'):
    user_id = d['choice'][5:]
  elif d['choice'].startswith('group_'):
    group_id = d['choice'][6:]
  
  d['report'] = _create_stats_report(user_id, group_id)
  s = stats.getStats()
  d['last_tally'] = datetime.datetime.fromtimestamp(s.getComputeTime()).strftime('%B %d, %Y')
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
  d['group_dn'] = d['user']['groupDn']
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

@uic.admin_login_required
def new_account(request, ssl=False):
  d = { 'menu_item' : 'ui_admin.new_account' }
  # id : [defaultvalue, label, type, help_text]
  field_info = { \
      'todays_date': [datetime.datetime.now().strftime("%m/%d/%Y"), "Today's date", "text", ""], \
      'submitters_name': ["", "Your name", "text", ""], \
      'acct_name': ["", "Account name", "text", "Choose a name that is lowercase, 10 characters or less; no spaces.  Underscore or dash ok"], \
      'acct_email': ["", "Email Address", "text", "To be associated with the account"], \
      'primary_contact': ["", "Primary contact", "text", "An individual associated with this account"], \
      'contact_email': ["", "Contact's email address", "text", ""], \
      'contact_phone': ["", "Contact's phone number", "text", ""], \
      'contact_fax': ["", "Contact's fax number", "text", ""], \
      'org': ["", "Organization", "text", ""], \
      'org_acroynm': ["", "Organization acronym", "text", "Suggest an acronym that is between 3-10 characters in length.  It will be used for identification purposes"], \
      'org_www': ["", "Organization's web address", "text", ""], \
      'mailing_address1': ["", "Address line 1", "text", ""], \
      'mailing_address2': ["", "Address line 2", "text", ""], \
      'mailing_city': ["", "City", "text", ""], \
      'mailing_state': ["", "State", "text", ""], \
      'mailing_zip': ["", "Zip code", "text", ""], \
      'mailing_country': ["", "Country", "text", ""], \
      'identifiers': ["", "Identifiers", "ARKs|DOIs and ARKs", "This choice affects the subscription pricing. If you have questions, please enter them below."], \
      'created_before': ["", "Have you created DOIs or ARKs before?", "NO|YES", ""], \
      'internal_identifiers': ["", "Do you use any internal or local identifiers?", "NO|YES", ""], \
      'identifier_plans': ["", "How do you plan to use identifiers in the next year?", "long_text", ""], \
      'comments': ["", "Comments or questions?", "long_text", ""] }
  
  field_order = ("todays_date submitters_name acct_name acct_email " + \
    "primary_contact contact_email contact_phone contact_fax org " + \
    "org_acroynm org_www mailing_address1 mailing_address2 mailing_city " + \
    "mailing_state mailing_zip mailing_country identifiers created_before " + \
    "internal_identifiers identifier_plans comments").split()
  
  #populate form values back into form
  if request.method == "POST":
    message = ""
    for key in field_order:
      if key in request.POST:
        field_info[key][0] = request.POST[key]
        v = (request.POST[key] if key in request.POST else '')
        message += anvl.formatPair(key, v)
    emails = [x.strip() for x in uic.new_account_email.split(',')]
    #print "new ezid account: " + request.POST['acct_name']
    #print message
    django.core.mail.send_mail("new ezid account: " + request.POST['acct_name'], message,
                               django.conf.settings.SERVER_EMAIL, emails)
    django.contrib.messages.success(request, "Form information has been emailed.")
    d['field_info'], d['field_order'] = field_info, field_order
    return uic.render(request, 'admin/new_account_display', d)
  
  d['field_info'], d['field_order'] = field_info, field_order
  return uic.render(request, 'admin/new_account', d)

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
  

def _month_range_for_display(user, group):
  """
  Produces a list of year-month strings which goes from the earliest
  data available for the user, group specified (use None for non) until now.
  """
  dates = _get_month_range(datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime.now())
  s = stats.getStats()
  num = None
  for date in dates:
    #try:
    num = s.query((date.strftime("%Y-%m"), user, group, None, None), False)
    #except AssertionError:
    #  num = 0
    if num > 0: break
  if date.strftime("%Y-%m") == datetime.datetime.now().strftime("%Y-%m") and num < 1:
    return []
  return [x.strftime("%Y-%m") for x in _get_month_range(date, datetime.datetime.now())]
    
def _get_month_range(dt1, dt2):
  """
  Creates a month range from the month/year of date1 to month/year of date2
  """
  #dt1, dt2 = datetime.datetime(2005, 1, 1, 0, 0), datetime.datetime.now()
  start_month=dt1.month
  end_months=(dt2.year-dt1.year)*12 + dt2.month+1
  dates=[datetime.datetime(year=yr, month=mn, day=1) for (yr, mn) in (
          ((m - 1) / 12 + dt1.year, (m - 1) % 12 + 1) for m in range(start_month, end_months)
      )]
  return dates

def _insertCommas (n):
  s = ""
  while n >= 1000:
    n, r = divmod(n, 1000)
    s = ",%03d%s" % (r, s)
  return "%d%s" % (n, s)

def _create_stats_report(user, group):
  """Create a stats report based on the user and group (or None, None) for all"""
  s = stats.getStats()
  months = _month_range_for_display(user,group)
  rows =[]
  
  position = {'ARK': 1, 'DOI': 3, 'URN': 5}
  id_types = ['ARK', 'DOI', 'URN']
  tallies = {'ARK': 0, 'DOI': 0, 'URN': 0}
  meta_tallies = {'ARK': 0.0, 'DOI': 0.0, 'URN': 0.0}
  
  for month in months:
    a=[0]*7 #create dict of zeroes, length 7
    a[0] = month
    for id_type in id_types:
      ids = s.query((month, user, group, id_type, None), False)
      ids_w_meta = float(s.query((month, user, group, id_type, "True"), False))
      tallies[id_type] = tallies[id_type] + ids
      meta_tallies[id_type] = meta_tallies[id_type] + ids_w_meta
      if ids == 0:
        percent_meta = "N/A"
      else:
        percent_meta = "%0.1f" % (ids_w_meta / ids * 100) + "%"
      a[position[id_type]] = _insertCommas(ids)
      a[position[id_type] + 1] = percent_meta
    rows.append(a)
    
  if len(rows) > 0:
    a=[0]*7 #create dict of zeroes, length 7
    a[0] = "Total"
    for id_type in id_types:
      if tallies[id_type] == 0:
        percent_meta = "N/A"
      else:
        percent_meta = "%0.1f" % (meta_tallies[id_type] / tallies[id_type] * 100) + "%"
      a[position[id_type]] = _insertCommas(tallies[id_type])
      a[position[id_type] + 1] = percent_meta
    rows.append(a)
  return rows
