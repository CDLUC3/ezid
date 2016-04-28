import ui_common as uic
import django.contrib.messages
import re
import ezidapp.models
import useradmin
import stats
import datetime
from collections import *


@uic.admin_login_required
def index(request, ssl=False):
  d = { 'menu_item' : 'ui_admin.index'}
  return uic.render(request, 'admin-old/index', d)

@uic.admin_login_required
def usage(request, ssl=False):
  d = { 'menu_item' : 'ui_admin.usage'}
  #make select list choices
  users = ezidapp.models.StoreUser.objects.all().order_by("username")
  groups = ezidapp.models.StoreGroup.objects.all().order_by("groupname")
  user_choices = [("user_" + x.pid, x.username) for x in users]
  group_choices = [("group_" + x.pid, x.groupname) for x in groups]
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
 
