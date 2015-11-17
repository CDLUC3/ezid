import ui_common as uic
import userauth, useradmin
import django.contrib.messages
import form_objects
import re
import time
from django.shortcuts import redirect

def edit(request, ssl=False):
  """Edit account information form"""
  d = { 'menu_item' : 'ui_account.edit'}
  if "auth" not in request.session: return uic.unauthorized(request)
  d['username'] = request.session['auth'].user[0]
  #used to do the following only for GET, but needed for post also to compare what has changed
  r = useradmin.getAccountProfile(d['username'])
  if type(r) is str:
    django.contrib.messages.error(request, r)
    return redirect('ui_home.index')
  r2 = useradmin.getContactInfo(d['username'])
  if type(r2) is str:
    django.contrib.messages.error(request, r2)
    return redirect("ui_home.index")
  r.update(r2)
  d.update(r)
  # ToDo: Replace with proxy data .... Is this line even needed?
  if not 'ezidCoOwners' in d: d['ezidCoOwners'] = ''
  if request.method == "GET":
    d['form'] = form_objects.UserForm(d, username=d['username'])
  else:
    d['form'] = form_objects.UserForm(request.POST, username=d['username'])
    if d['form'].is_valid():
      update_edit_user(request, d['form'].has_changed())
  return uic.render(request, "account/edit", d)

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
      return uic.badRequest(request)
    auth = userauth.authenticate(request.POST["username"],
      request.POST["password"])
    if type(auth) is str:
      django.contrib.messages.error(request, uic.formatError(auth))
      return uic.render(request, 'account/login', d)
    if auth:
      request.session["auth"] = auth
      django.contrib.messages.success(request, "Login successful.")
      #request.session['hide_alert'] = False
      if 'redirect_to' in request.POST:
        return redirect(_filterBadRedirect(request.POST['redirect_to']))
      if 'redirect_to' in request.session and request.session['redirect_to']:
        return redirect(_filterBadRedirect(request.session['redirect_to']))
      else:
        return redirect('ui_home.index')
    else:
      django.contrib.messages.error(request, "Login failed.")
      return uic.render(request, "account/login", d)
  else:
    return uic.methodNotAllowed(request)

def _filterBadRedirect(url):
  return "/" if url.startswith("/login") else url

def logout(request):
  """
  Logs the user out and redirects to the home page.
  """
  d = { 'menu_item' : 'ui_null.null'}
  if request.method != "GET": return uic.methodNotAllowed(request)
  request.session.flush()
  django.contrib.messages.success(request, "You have been logged out.")
  return redirect("ui_home.index")

def update_edit_user(request, basic_info_changed):
  """method to update the user editing his information.  Not a view for a page"""
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
    if basic_info_changed: django.contrib.messages.success(request, "Your information has been updated.")
  
  if request.POST['pwcurrent'].strip() != '':
    r = useradmin.resetPassword(uid, request.POST["pwnew"].strip())
    if type(r) is str:
      django.contrib.messages.error(request, r)
    else:
      django.contrib.messages.success(request, "Your password has been updated.")
      
def pwreset(request, pwrr, ssl=False):
  """
  Handles all GET and POST interactions related to password resets.
  """
  if pwrr:
    r = useradmin.decodePasswordResetRequest(pwrr)
    if not r:
      django.contrib.messages.error(request, "Invalid password reset request.")
      return uic.redirect("/")
    username, t = r
    if int(time.time())-t >= 24*60*60:
      django.contrib.messages.error(request,
        "Password reset request has expired.")
      return uic.redirect("/")
    if request.method == "GET":
      return uic.render(request, "account/pwreset2", { "pwrr": pwrr,
        "username": username, 'menu_item' : 'ui_null.null' })
    elif request.method == "POST":
      if "password" not in request.POST or "confirm" not in request.POST:
        return uic.badRequest(request)
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
        return uic.redirect("/")
    else:
      return uic.methodNotAllowed(request)
  else:
    if request.method == "GET":
      return uic.render(request, "account/pwreset1", {'menu_item' : 'ui_null.null'})
    elif request.method == "POST":
      if "username" not in request.POST or "email" not in request.POST:
        return uic.badRequest(request)
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
        return uic.redirect("/")
    else:
      return uic.methodNotAllowed(request)
