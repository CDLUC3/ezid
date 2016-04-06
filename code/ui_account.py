import ui_common as uic
import userauth, useradmin
import django.contrib.auth
import django.contrib.messages
import django.core.urlresolvers
import django.utils.http
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
    orig_vals = uic.extract(d, ['givenName', 'sn', 'mail', 'telephoneNumber', 'ezidCoOwners'])
    form_vals = uic.extract(request.POST, \
                ['givenName', 'sn', 'mail', 'telephoneNumber', 'ezidCoOwners'])
    d.update(form_vals)
    if validate_edit_user(request):
      update_edit_user(request, orig_vals != form_vals)
  return uic.render(request, "account/edit", d)

def login (request, ssl=False):
  """
  Renders the login page (GET) or processes a login form submission
  (POST).  A successful login redirects to the URL specified by
  ?next=... or, failing that, the home page.
  """
  d = { "menu_item": "ui_null.null" }
  if request.method == "GET":
    if "next" in request.GET:
      try:
        m = django.core.urlresolvers.resolve(request.GET["next"])
        if m.app_name == "admin":
          django.contrib.messages.error(request,
            "You must be logged in as an administrator to view this page.")
      except django.core.urlresolvers.Resolver404:
        pass
      d["next"] = request.GET["next"]
    else:
      d["next"] = django.core.urlresolvers.reverse("ui_home.index")
    return uic.render(request, "account/login", d)
  elif request.method == "POST":
    if "username" not in request.POST or "password" not in request.POST or\
      "next" not in request.POST:
      return uic.badRequest()
    d.update(uic.extract(request.POST, ["username", "password", "next"]))
    auth = userauth.authenticate(d["username"], d["password"])
    if type(auth) is str:
      django.contrib.messages.error(request, uic.formatError(auth))
      return uic.render(request, "account/login", d)
    if auth:
      request.session["auth"] = auth
      django.contrib.messages.success(request, "Login successful.")
      if d["username"] == uic.adminUsername:
        # Add session variables to support the Django admin interface.
        django.contrib.auth.login(request,
          django.contrib.auth.authenticate(username=d["username"],
          password=d["password"]))
      if django.utils.http.is_safe_url(url=d["next"], host=request.get_host()):
        return redirect(d["next"])
      else:
        return redirect("ui_home.index")
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

def validate_edit_user(request):
  """validates that the fields required to update a user are set, not a view for a page"""
  valid_form = True
  fields = ['givenName', 'sn', 'mail', 'telephoneNumber', 'ezidCoOwners', 'pwcurrent','pwnew', 'pwconfirm']
  
  for field in fields:
    if not field in request.POST:
      django.contrib.messages.error(request, "Form submission error.")
      return False
  
  required_fields = {'sn': 'Last name', 'mail': 'Email address'}
  for field in required_fields:
    if request.POST[field].strip() == '':
      django.contrib.messages.error(request, required_fields[field] + " must be filled in.")
      valid_form = False
  
  if not re.match('^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$', request.POST['mail'], re.IGNORECASE):
    django.contrib.messages.error(request, "Please enter a valid email address.")
    valid_form = False
  
  if request.POST['ezidCoOwners'] != '':
    coowners = [co.strip() for co in request.POST['ezidCoOwners'].split(',')]
    for coowner in coowners:
      #import pdb; pdb.set_trace()
      try:
        idmap.getUserId(coowner)
      except AssertionError:
        django.contrib.messages.error(request, coowner + " is not a correct username for a co-owner.")
        valid_form = False
  
  if not request.POST['pwcurrent'].strip() == '':
    auth = userauth.authenticate(request.session['auth'].user[0], request.POST["pwcurrent"])
    if type(auth) is str or not auth:
      django.contrib.messages.error(request, "Your current password is incorrect.")
      valid_form = False
    if request.POST['pwnew'] != request.POST['pwconfirm']:
      django.contrib.messages.error(request, "Your new and confirmed passwords do not match.")
      valid_form = False
    if request.POST['pwnew'] == '' or request.POST['pwconfirm'] == '':
      django.contrib.messages.error(request, "Your new password cannot be empty.")
      valid_form = False
  return valid_form
  
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
        return uic.redirect("/")
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
        return uic.redirect("/")
    else:
      return uic.methodNotAllowed()
