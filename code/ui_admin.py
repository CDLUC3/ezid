import ui_common as uic
import django.contrib.messages
import os
import ezidadmin
import config
import idmap
import re
import ezidapp.models.shoulder
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
  return uic.render(request, 'admin-old/index', d)

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
  
  d['report'] = _create_stats_report(user_id, group_id)[::-1]
  if len(d['report']) > 0:
    d['totals'] = d['report'][0]
    d['report'] = d['report'][1:]
  s = stats.getStats()
  last_calc = datetime.datetime.fromtimestamp(s.getComputeTime())
  d['last_tally'] = last_calc.strftime('%B %d, %Y')
  d['yearly'] = _year_totals(user_id, group_id, last_calc)
  
  return uic.render(request, 'admin-old/usage', d)

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
  if request.method == "GET":
    REQUEST = request.GET
  else:
    REQUEST = request.POST
  if 'user' in REQUEST and REQUEST['user'] in users_by_dn:
    d['selected_user'] = users_by_dn[REQUEST['user']]
  else:
    d['selected_user'] = d['users'][0]
  if d['selected_user']['sn'] == 'please supply':
    d['selected_user']['sn'] = ''
  if d['selected_user']['mail'] == 'please supply':
    d['selected_user']['mail'] = ''
  
  d['groups'] = ezidadmin.getGroups()
  d['groups'].sort(key=lambda i: i['gid'].lower())
  d['group'] = idmap.getGroupId(d['selected_user']['groupGid'])
  d['group_dn'] = d['selected_user']['groupDn']
  #now for saving
  if request.method == "POST" and request.POST['user'] == request.POST['original_user']:
    u, p = d['selected_user'], request.POST
    d['group_dn'] = p['group_dn']
    u['givenName'], u['sn'], u['mail'], u['telephoneNumber'], u['description'] = \
      p['givenName'], p['sn'], p['mail'], p['telephoneNumber'], p['description']
    u['ezidCoOwners'] = ','.join([x.strip() for x in p['ezidCoOwners'].strip().split("\n")])
    if validate_edit_user(request, u):
      d['selected_user']['currentlyEnabled'] = update_edit_user(request, u)
      #if group has changed, update
      if p['group_dn'] != u['groupDn']:
        res = ezidadmin.changeGroup(u['uid'], p['group_dn'], \
                request.session["auth"].user, request.session["auth"].group)
        if type(res) == str:
          django.contrib.messages.error(request, res)
    else:
      if 'currentlyEnabled' in request.POST and request.POST['currentlyEnabled'].lower() == 'true':
        d['selected_user']['currentlyEnabled'] = 'true'
      else:
        d['selected_user']['currentlyEnabled'] = 'false'
  d['ezidCoOwners'] = "\n".join([x.strip() for x in d['selected_user']['ezidCoOwners'].split(',')])
  return uic.render(request, 'admin-old/manage_users', d)

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
  if request.method == "GET":
    REQUEST = request.GET
  else:
    REQUEST = request.POST
  if len(d['groups']) > 0:
    if 'group' in REQUEST:
      if REQUEST['group'] in groups_by_dn:
        d['group'] = groups_by_dn[REQUEST['group']]
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
    grp = d['group']
    grp['description'] = P['description']
    if 'agreementOnFile' in P and P['agreementOnFile'] == 'True':
      grp['agreementOnFile'] = True
    else:
      grp['agreementOnFile'] = False
    if 'crossrefEnabled' in P and P['crossrefEnabled'] == 'True':
      grp['crossrefEnabled'] = True
    else:
      grp['crossrefEnabled'] = False
    if 'crossrefSendMailOnError' in P and P['crossrefSendMailOnError'] == 'True':
      grp['crossrefSendMailOnError'] = True
    else:
      grp['crossrefSendMailOnError'] = False
    grp['crossrefMail'] = P['crossrefMail']
    sels = P.getlist('shoulderList')
    if '-' in sels:
      sels.remove('-')
    if len(sels) < 1:
      validated = False
      django.contrib.messages.error(request, "You must select at least one shoulder from the shoulder list (or choose NONE).")
    if len(sels) > 1 and ('*' in sels or 'NONE' in sels):
      validated = False
      django.contrib.messages.error(request, "If you select * or NONE you may not select other items in the shoulder list.")
    if grp['crossrefEnabled']:
      for email in [x.strip() for x in grp['crossrefMail'].split(',')\
        if len(x.strip()) > 0]:
          if not _is_email_valid(email):
            django.contrib.messages.error(request, email + " is not a valid email address. Please enter a valid email address.")
            validated = False
    if validated:
      r = ezidadmin.updateGroup(grp["dn"], grp["description"].strip(),
        grp["agreementOnFile"], " ".join(sels),
        grp["crossrefEnabled"], grp['crossrefMail'], grp['crossrefSendMailOnError'],
        request.session["auth"].user, request.session["auth"].group)
      if type(r) is str:
        django.contrib.messages.error(request, r)
      else:
        django.contrib.messages.success(request, "Successfully updated group")
  else:
    sels = d['group']['shoulderList'].split()
  d['selected_shoulders'], d['deselected_shoulders'] = select_shoulder_lists(sels)
  return uic.render(request, 'admin-old/manage_groups', d)

def select_shoulder_lists(selected_val_list):
  """Makes list of selected and deselected shoulders in format [value, friendly label]
  and returns (selected_list, deselected_list)"""
  #make lists of selected and deselected shoulders
  sorted_shoulders = sorted([{\
    "name": s.name+" "+s.type, "prefix": s.prefix,
    "label": s.prefix }\
    for s in ezidapp.models.shoulder.getAll() if not s.isTest],
    key=lambda p: (p['name'] + ' ' + p['prefix']).lower())
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
  er = django.contrib.messages.error
  post = request.POST
  
  required_fields = {'sn': 'Last name', 'mail': 'Email address'}
  for field in required_fields:
    if user_obj[field].strip() == '':
      er(request, required_fields[field] + " must be filled in.")
  
  if not _is_email_valid(user_obj['mail']):
    er(request, "Please enter a valid email address.")
  
  if user_obj['ezidCoOwners'] != '':
    coowners = [co.strip() for co in user_obj['ezidCoOwners'].split(',')]
    for coowner in coowners:
      try:
        idmap.getUserId(coowner)
      except AssertionError:
        er(request, coowner + " is not a correct handle for a co-owner.")
  
  if not post['userPassword'].strip() == '':
    if len(post['userPassword'].strip()) < 6:
      er(request, "Please use a password length of at least 6 characters.")

  if post['telephoneNumber'] != '' and (not re.match(r'^[0-9\.\-() +]+$', post['telephoneNumber'], re.IGNORECASE)):
    er(request, "Please enter a valid phone number.")
    
  return  len(django.contrib.messages.api.get_messages(request)) < 1

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
  data available for the user, group specified (use None for none) until now.
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

def _insertCommas(n):
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
        percent_meta = "0%"
      else:
        percent_meta = str(int((ids_w_meta / ids * 100))) + "%"
      a[position[id_type]] = _insertCommas(ids)
      a[position[id_type] + 1] = percent_meta
    rows.append(a)
    
  if len(rows) > 0:
    a=[0]*9 #create list of zeroes, length 7
    a[0] = "Total"
    for id_type in id_types:
      if tallies[id_type] == 0:
        percent_meta = "0%"
      else:
        percent_meta = str(int((meta_tallies[id_type] / tallies[id_type] * 100))) + "%"
      a[position[id_type]] = _insertCommas(tallies[id_type])
      a[position[id_type] + 1] = percent_meta
    grand_tot_items = sum(tallies.values())
    a[8] = str(int(sum(meta_tallies.values()) / grand_tot_items * 100)) + "%"
    a[7] = _insertCommas(grand_tot_items)
    rows.append(a)
  return rows

def _monthdelta(date, delta):
  m, y = (date.month+delta) % 12, date.year + ((date.month)+delta-1) // 12
  if not m: m = 12
  d = min(date.day, [31,
      29 if y%4==0 and not y%400==0 else 28,31,30,31,30,31,31,30,31,30,31][m-1])
  return date.replace(day=d,month=m, year=y)

def _year_totals(user, group, last_calc):
  """creates totals for the previous year (only whole months
  for which stats have been calculated)"""
  dt_start = datetime.datetime(last_calc.year - 1, last_calc.month, last_calc.day)
  dt_end = _monthdelta(last_calc, -1)
  months = [x.strftime("%Y-%m") for x in _get_month_range(dt_start, dt_end)]
  tot = 0
  meta = 0
  s = stats.getStats()
  id_types = ['ARK', 'DOI', 'URN']
  id_totals = dict((key, 0) for key in id_types)
  id_meta = dict((key, 0) for key in id_types)
  
  for month in months:
    tot = tot + s.query((month, user, group, None, None), False)
    meta = meta + s.query((month, user, group, None, "True"), False)
    for t in id_types:
      id_totals[t] = id_totals[t] + s.query((month, user, group, t, None), False)
      id_meta[t] = id_meta[t] + s.query((month, user, group, t, "True"), False)

  return_vals = {'text': "Totals from " + months[0] + " through " + months[-1],
                 'totals': _insertCommas(tot)}
  for t in id_types:
    return_vals[t+'_total'] = _insertCommas(id_totals[t])
    if id_totals[t] == 0:
      return_vals[t+'_percent'] = '0%'
    else:
      return_vals[t+'_percent'] = str(int((float(id_meta[t]) / id_totals[t] * 100.0))) + "%"
  if tot == 0:
    return_vals['tot_percent'] = '0%'
  else:
    return_vals['tot_percent'] = str(int((float(meta) / tot * 100.0))) + "%"
  return return_vals
 
def _is_email_valid(email):
  if not re.match('^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$', email, re.IGNORECASE):
    return False
  else: return True
 
