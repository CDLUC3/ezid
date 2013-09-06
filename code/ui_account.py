import ui_common as uic
import userauth, useradmin
import django.contrib.messages
import idmap
import re
import time
from django.shortcuts import redirect

def edit(request, ssl=False):
  """Edit account information form"""
  d = { 'menu_item' : 'ui_null.null'}
  if "auth" not in request.session: return uic.unauthorized()
  d['username'] = request.session['auth'].user[0]
  #used to do the following only for GET, but needed for post also to compare what has changed
  r = useradmin.getAccountProfile(request.session["auth"].user[0])
  if type(r) is str:
    django.contrib.messages.error(request, r)
    return redirect('ui_home.index')
  r2 = useradmin.getContactInfo(request.session["auth"].user[0])
  if type(r2) is str:
    django.contrib.messages.error(request, r2)
    return redirect("ui_home.index")
  r.update(r2)
  d.update(r)
  if not 'ezidCoOwners' in d:
    d['ezidCoOwners'] = ''
      
  if request.method == "POST":
    form_vals = uic.extract(request.POST, \
                ['givenName', 'sn', 'mail', 'telephoneNumber', 'ezidCoOwners'])
    d.update(form_vals)
    if _validate_edit_user(request):
      _update_edit_user(request)
  return uic.render(request, "account/edit", d)

def change_pwd(request, ssl=False):
  """Change the password form"""
  d = { 'menu_item' : 'ui_null.null'}
  if "auth" not in request.session: return uic.unauthorized()
  
  if request.method == "POST":
    d['pwcurrent'] = request.POST['pwcurrent']
    d['pwnew'] = request.POST['pwnew']
    d['pwconfirm'] = request.POST['pwconfirm']
    if not request.POST['pwcurrent'].strip() == '':
      uid = request.session['auth'].user[0]
      auth = userauth.authenticate(uid, request.POST["pwcurrent"])
      if type(auth) is str or not auth:
        django.contrib.messages.error(request, "Your current password is incorrect.")
      if request.POST['pwnew'] != request.POST['pwconfirm']:
        django.contrib.messages.error(request, "Your new and confirmed passwords do not match.")
      if request.POST['pwnew'] == '' or request.POST['pwconfirm'] == '':
        django.contrib.messages.error(request, "Your new password cannot be empty.")
      if len(django.contrib.messages.api.get_messages(request)) > 0:
        return uic.render(request, "account/change_pwd", d)
    
      r = useradmin.resetPassword(uid, request.POST["pwnew"].strip())
      if type(r) is str:
        django.contrib.messages.error(request, r)
      else:
        django.contrib.messages.success(request, "Your password has been updated.")
  return uic.render(request, "account/change_pwd", d)

def user_stats(request, ssl=False):
  """display user stats"""
  d = { 'menu_item' : 'ui_null.null'}
  if "auth" not in request.session: return uic.unauthorized()
  return uic.render(request, "account/user_stats", d)

def login(request, ssl=False):
  """
  Renders the login page (GET) or processes a login form submission
  (POST).  A successful login redirects to the home page.
  """
  d = { 'menu_item' : 'ui_null.null'}
  if request.method == "GET":
    return uic.render(request, 'account/login', d)
  elif request.method == "POST":
    d.update(uic.extract(request.POST, ['username', 'password']))
    if "username" not in request.POST or "password" not in request.POST:
      return uic.badRequest()
    auth = userauth.authenticate(request.POST["username"],
      request.POST["password"])
    if type(auth) is str:
      django.contrib.messages.error(request, uic.formatError(auth))
      return uic.render(request, 'account/login', d)
    if auth:
      p = uic.getPrefixes(auth.user, auth.group)
      if type(p) is str:
        django.contrib.messages.error(request, uic.formatError(p))
        return uic.render(request, 'account/login', d)
      request.session["auth"] = auth
      request.session["prefixes"] = p
      django.contrib.messages.success(request, "Login successful.")
      #request.session['hide_alert'] = False
      if 'redirect_to' in request.session and request.session['redirect_to']:
        return redirect(request.session['redirect_to'])
      else:
        return redirect('ui_home.index')
    else:
      django.contrib.messages.error(request, "Login failed.")
      return uic.render(request, "account/login", d)
  else:
    return uic.methodNotAllowed()

def logout(request):
  """
  Logs the user out and redirects to the home page.
  """
  d = { 'menu_item' : 'ui_null.null'}
  if request.method != "GET": return uic.methodNotAllowed()
  request.session.flush()
  django.contrib.messages.success(request, "You have been logged out.")
  return redirect("ui_home.index")

def _validate_edit_user(request):
  """validates that the fields required to update a user are set, not a view for a page"""
  er = django.contrib.messages.error
  post = request.POST
  
  fields = ['givenName', 'sn', 'mail', 'telephoneNumber', 'ezidCoOwners']
  
  for field in fields:
    if not field in request.POST:
      django.contrib.messages.error(request, "Form submission error.")
      return False
  
  required_fields = {'sn': 'Last name', 'mail': 'Email address'}
  for field in required_fields:
    if post[field].strip() == '':
      er(request, required_fields[field] + " must be filled in.")
  if len(django.contrib.messages.api.get_messages(request)) > 0:
    return False
  
  if not re.match('^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$', post['mail'], re.IGNORECASE):
    er(request, "Please enter a valid email address.")
  
  if post['ezidCoOwners'] != '':
    coowners = [co.strip() for co in post['ezidCoOwners'].split(',')]
    for coowner in coowners:
      try:
        idmap.getUserId(coowner)
      except AssertionError:
        er(request, coowner + " is not a correct username for a co-owner.")
        
  return len(django.contrib.messages.api.get_messages(request)) < 1
  
def _update_edit_user(request):
  """method to update the user editing his information"""
  uid = request.session['auth'].user[0]
  di = {}
  for item in ['givenName', 'sn', 'mail', 'telephoneNumber']:
    di[item] = request.POST[item].strip()
  r = useradmin.setContactInfo(uid, di)
  if type(r) is str: django.contrib.messages.error(request, r)
  if request.POST['ezidCoOwners'].strip() == '':
    r = useradmin.setAccountProfile(uid, '')
  else:
    r = useradmin.setAccountProfile(uid, request.POST['ezidCoOwners'].strip())
  if type(r) is str:
    django.contrib.messages.error(request, r)
  else:
    django.contrib.messages.success(request, "Your information has been updated.")
      
def pwreset(request, pwrr, ssl=False):
  """
  Handles all GET and POST interactions related to password resets.
  """
  if pwrr:
    r = useradmin.decodePasswordResetRequest(pwrr)
    if not r:
      django.contrib.messages.error(request, "Invalid password reset request.")
      return uic.redirect("/ezid/")
    username, t = r
    if int(time.time())-t >= 24*60*60:
      django.contrib.messages.error(request,
        "Password reset request has expired.")
      return uic.redirect("/ezid/")
    if request.method == "GET":
      return uic.render(request, "account/pwreset2", { "pwrr": pwrr,
        "username": username, 'menu_item' : 'ui_null.null' })
    elif request.method == "POST":
      if "password" not in request.POST or "confirm" not in request.POST:
        return uic.badRequest()
      password = request.POST["password"]
      confirm = request.POST["confirm"]
      if password != confirm:
        django.contrib.messages.error(request,
          "Password and confirmation do not match.")
        return uic.render(request, "account/pwreset2", { "pwrr": pwrr,
          "username": username, 'menu_item' : 'ui_null.null' })
      if password == "":
        django.contrib.messages.error(request, "Password required.")
        return uic.render(request, "account/pwreset2", { "pwrr": pwrr,
          "username": username, 'menu_item' : 'ui_null.null' })
      r = useradmin.resetPassword(username, password)
      if type(r) is str:
        django.contrib.messages.error(request, r)
        return uic.render(request, "account/pwreset2", { "pwrr": pwrr,
          "username": username,  'menu_item' : 'ui_null.null' })
      else:
        django.contrib.messages.success(request, "Password changed.")
        return uic.redirect("/ezid/")
    else:
      return uic.methodNotAllowed()
  else:
    if request.method == "GET":
      return uic.render(request, "account/pwreset1", {'menu_item' : 'ui_null.null'})
    elif request.method == "POST":
      if "username" not in request.POST or "email" not in request.POST:
        return uic.badRequest()
      username = request.POST["username"].strip()
      email = request.POST["email"].strip()
      if username == "":
        django.contrib.messages.error(request, "Username required.")
        return uic.render(request, "account/pwreset1", { "email": email,  'menu_item' : 'ui_null.null' })
      if email == "":
        django.contrib.messages.error(request, "Email address required.")
        return uic.render(request, "account/pwreset1", { "username": username,  'menu_item' : 'ui_null.null' })
      r = useradmin.sendPasswordResetEmail(username, email)
      if type(r) is str:
        django.contrib.messages.error(request, r)
        return uic.render(request, "account/pwreset1", { "username": username,
          "email": email,  'menu_item' : 'ui_null.null' })
      else:
        django.contrib.messages.success(request, "Email sent.")
        return uic.redirect("/ezid/")
    else:
      return uic.methodNotAllowed()