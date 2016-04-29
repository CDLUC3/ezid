import ui_common as uic
import django.contrib.messages
import re
import ezidapp.models
import useradmin
import stats
import datetime

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

  s = stats.getStats()
  table = s.getTable(owner=user_id, group=group_id, useLocalNames=False)
  d["months"] = _computeMonths(table)
  if len(d["months"]) > 0:
    d["totals"] = _computeTotals(table)
    lastYear = table[-12:]
    d["lastYear"] = _computeTotals(lastYear)
    d["lastYearFrom"] = lastYear[0][0]
    d["lastYearTo"] = lastYear[-1][0]

  last_calc = datetime.datetime.fromtimestamp(s.getComputeTime())
  d['last_tally'] = last_calc.strftime('%B %d, %Y')
  return uic.render(request, 'admin-old/usage', d)

def _percent (m, n):
  if n == 0:
    return 0
  else:
    return m*100/n

def _insertCommas (n):
  s = ""
  while n >= 1000:
    n, r = divmod(n, 1000)
    s = ",%03d%s" % (r, s)
  return "%d%s" % (n, s)

def _computeMonths (table):
  months = []
  for month, d in table:
    months.append({ "month": month })
    for type in ["ARK", "DOI"]:
      total = d.get((type, "True"), 0) + d.get((type, "False"), 0)
      months[-1][type] = { "total": _insertCommas(total),
        "hasMetadataPercentage":\
        str(_percent(d.get((type, "True"), 0), total)) }
  return months[::-1]

def _computeTotals (table):
  if len(table) == 0: table = [("dummy", {})]
  data = {}
  for row in table:
    for type in ["ARK", "DOI"]:
      for hasMetadata in ["True", "False"]:
        t = (type, hasMetadata)
        data[t] = data.get(t, 0) + row[1].get(t, 0)
        data[("grand", hasMetadata)] =\
          data.get(("grand", hasMetadata), 0) + row[1].get(t, 0)
  totals = {}
  for type in ["ARK", "DOI", "grand"]:
    total = data[(type, "True")] + data[(type, "False")]
    totals[type] = { "total": _insertCommas(total),
      "hasMetadataPercentage": str(_percent(data[(type, "True")], total)) }
  return totals

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
  
def _is_email_valid(email):
  if not re.match('^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$', email, re.IGNORECASE):
    return False
  else: return True
