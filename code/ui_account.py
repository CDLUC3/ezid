import ui_common as uic
import userauth
import django.conf
import django.contrib.messages
import django.core.mail
import django.core.urlresolvers
import django.core.validators
import django.utils.http
import django.db.transaction
import hashlib
import re
import time
import urllib
from django.shortcuts import redirect
import ezidapp.admin
import ezidapp.models

@uic.user_login_required
def edit(request, ssl=False):
  """Edit account information form"""
  d = { 'menu_item' : 'ui_null.null'}
  user = userauth.getUser(request)
  d["username"] = user.username
  d["givenName"] = user.primaryContactName
  d["sn"] = ""
  d["mail"] = user.primaryContactEmail
  d["telephoneNumber"] = user.primaryContactPhone
  d["ezidCoOwners"] =\
    ", ".join(u.username for u in user.proxies.all().order_by("username"))
      
  if request.method == "POST":
    orig_vals = uic.extract(d, ['givenName', 'sn', 'mail', 'telephoneNumber', 'ezidCoOwners'])
    form_vals = uic.extract(request.POST, \
                ['givenName', 'sn', 'mail', 'telephoneNumber', 'ezidCoOwners'])
    d.update(form_vals)
    if validate_edit_user(request, user):
      update_edit_user(request, user, orig_vals != form_vals)
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
    user = userauth.authenticate(d["username"], d["password"], request)
    if type(user) is str:
      django.contrib.messages.error(request, uic.formatError(user))
      return uic.render(request, "account/login", d)
    if user != None:
      django.contrib.messages.success(request, "Login successful.")
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

def validate_edit_user(request, user):
  """validates that the fields required to update a user are set, not a view for a page"""
  valid_form = True
  fields = ['givenName', 'sn', 'mail', 'telephoneNumber', 'ezidCoOwners', 'pwcurrent','pwnew', 'pwconfirm']
  
  for field in fields:
    if not field in request.POST:
      django.contrib.messages.error(request, "Form submission error.")
      return False
  
  required_fields = {'givenName': 'First name', 'mail': 'Email address'}
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
      u = ezidapp.models.getUserByUsername(coowner)
      if u == None or u == user or u.isAnonymous:
        django.contrib.messages.error(request, coowner + " is not a correct username for a co-owner.")
        valid_form = False
  
  if not request.POST['pwcurrent'].strip() == '':
    u = userauth.authenticate(user.username, request.POST["pwcurrent"])
    if type(u) is str or not u:
      django.contrib.messages.error(request, "Your current password is incorrect.")
      valid_form = False
    if request.POST['pwnew'] != request.POST['pwconfirm']:
      django.contrib.messages.error(request, "Your new and confirmed passwords do not match.")
      valid_form = False
    if request.POST['pwnew'] == '' or request.POST['pwconfirm'] == '':
      django.contrib.messages.error(request, "Your new password cannot be empty.")
      valid_form = False
  return valid_form
  
def update_edit_user(request, user, basic_info_changed):
  """method to update the user editing his information.  Not a view for a page"""
  d = request.POST
  try:
    with django.db.transaction.atomic():
      user.primaryContactName = d["givenName"] + " " + d["sn"]
      user.primaryContactEmail = d["mail"]
      user.primaryContactPhone = d["telephoneNumber"]
      user.proxies.clear()
      for coowner in [co.strip() for co in d["ezidCoOwners"].split(",")]:
        if coowner != "":
          user.proxies.add(ezidapp.models.getUserByUsername(coowner))
      if d["pwcurrent"].strip() != "": user.setPassword(d["pwnew"].strip())
      user.full_clean(validate_unique=False)
      user.save()
      ezidapp.admin.scheduleUserChangePostCommitActions(user)
  except django.core.validators.ValidationError, e:
    django.contrib.messages.error(request, str(e))
  else:
    if basic_info_changed:
      django.contrib.messages.success(request,
        "Your information has been updated.")
    if d["pwcurrent"].strip() != "":
      django.contrib.messages.success(request,
        "Your password has been updated.")
      
def pwreset(request, pwrr, ssl=False):
  """
  Handles all GET and POST interactions related to password resets.
  """
  if pwrr:
    r = decodePasswordResetRequest(pwrr)
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
      user = ezidapp.models.getUserByUsername(username)
      if user == None or user.isAnonymous:
        django.contrib.messages.error(request, "No such user.")
        return uic.render(request, "account/pwreset2", { "pwrr": pwrr,
          "username": username, 'menu_item' : 'ui_null.null' })
      with django.db.transaction.atomic():
        user.setPassword(password)
        user.save()
        ezidapp.admin.scheduleUserChangePostCommitActions(user)
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
      r = sendPasswordResetEmail(username, email)
      if type(r) is str:
        django.contrib.messages.error(request, r)
        return uic.render(request, "account/pwreset1", { "username": username,
          "email": email,  'menu_item' : 'ui_null.null' })
      else:
        django.contrib.messages.success(request, "Email sent.")
        return uic.redirect("/")
    else:
      return uic.methodNotAllowed()

def sendPasswordResetEmail (username, emailAddress):
  """
  Sends an email containing a password reset request link.  Returns
  None on success or a string message on error.
  """
  user = ezidapp.models.getUserByUsername(username)
  if user == None or user.isAnonymous: return "No such user."
  if emailAddress not in [user.accountEmail, user.primaryContactEmail,
    user.secondaryContactEmail]:
    return "Email address does not match any address registered for username."
  t = int(time.time())
  hash = hashlib.sha1("%s|%d|%s" % (username, t,
    django.conf.settings.SECRET_KEY)).hexdigest()[::4]
  link = "%s/account/pwreset/%s,%d,%s" %\
    (uic.ezidUrl, urllib.quote(username), t, hash)
  message = "You have requested to reset your EZID password.\n" +\
    "Click the link below to complete the process:\n\n" +\
    link + "\n\n" +\
    "Please do not reply to this email.\n"
  django.core.mail.send_mail("EZID password reset request", message,
    django.conf.settings.SERVER_EMAIL, [emailAddress])
  return None

def decodePasswordResetRequest (request):
  """
  Decodes a password reset request, returning a tuple (username,
  timestamp) on success or None on error.
  """
  m = re.match("/([^ ,]+),(\d+),([\da-f]+)$", request)
  if not m: return None
  username = m.group(1)
  t = m.group(2)
  hash = m.group(3)
  if hashlib.sha1("%s|%s|%s" % (username, t,
    django.conf.settings.SECRET_KEY)).hexdigest()[::4] != hash: return None
  return (username, int(t))
