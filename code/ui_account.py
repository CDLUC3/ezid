import ui_common as uic
import userauth
import django.conf
import django.contrib.messages
import django.core.mail
import django.core.urlresolvers
import django.core.validators
import django.utils.http
import django.db.transaction
import form_objects
import hashlib
import re
import time
import urllib
from django.shortcuts import redirect
import ezidapp.admin
import ezidapp.models
import json
from django.utils.translation import ugettext as _

ACCOUNT_FIELDS_EDITABLE = ['primaryContactName', 'primaryContactEmail', 'primaryContactPhone', 
           'secondaryContactName', 'secondaryContactEmail', 'secondaryContactPhone', 
           'accountDisplayName', 'accountEmail']

@uic.user_login_required
def edit(request, ssl=False):
  """Edit account information form"""
  d = { 'menu_item' : 'ui_account.edit'}
  user = userauth.getUser(request)
  d["username"] = user.username

  proxies_orig = [u.username for u in user.proxies.all().order_by("username")]
  d['proxy_users_choose'] = {u.username: u.displayName for u in\
    allUsersInRealm(user) if u.displayName != user.displayName}
  if request.method == "GET":
    d['primaryContactName'] = user.primaryContactName
    d['primaryContactEmail'] = user.primaryContactEmail
    d['primaryContactPhone'] = user.primaryContactPhone
    d['secondaryContactName'] = user.secondaryContactName
    d['secondaryContactEmail'] = user.secondaryContactEmail
    d['secondaryContactPhone'] = user.secondaryContactPhone
    d['accountDisplayName'] = user.displayName
    d['accountEmail'] = user.accountEmail
    if user.crossrefEnabled: d['crossrefEmail'] = user.crossrefEmail
    proxy_for_list = user.proxy_for.all().order_by("username")
    d['proxy_for'] = "<br/> ".join("[" + u.username + "]&nbsp;&nbsp;&nbsp;" + u.displayName \
      for u in proxy_for_list) if proxy_for_list else "N/A"
    d['proxy_users_picked_list'] = json.dumps(proxies_orig)
    d['proxy_users_picked'] = ', '.join(proxies_orig)
    d['form'] = form_objects.UserForm(d, user=user, username=d['username'], pw_reqd=False)
  else:
    # ToDo: Email new proxy users 
    d['form'] = form_objects.UserForm(request.POST, initial=d, user=user, username=d['username'], pw_reqd=False)
    basic_info_changed=False
    if d['form'].is_valid():
      if d['form'].has_changed():
        basic_info_changed = any(ch in d['form'].changed_data for ch in ACCOUNT_FIELDS_EDITABLE)
      # ToDo: Implement new proxies to be added
      _update_edit_user(request, user, None, basic_info_changed)
    else: # Form did not validate
      if '__all__' in d['form'].errors:
        # non_form_error, probably due to all fields being empty
        all_errors = ''
        errors = d['form'].errors['__all__']
        for e in errors:
          all_errors += e 
        django.contrib.messages.error(request, _("Change(s) could not be made.   ") + all_errors)
      else:
        err = _("Change(s) could not be made.  Please check the highlighted field(s) below for details.")
        django.contrib.messages.error(request, err)
  return uic.render(request, "account/edit", d)

def allUsersInRealm(user):
  realmusers = []
  for group in user.realm.groups.all():
    realmusers.extend(group.users.all())
  return sorted(realmusers, key=lambda k: k.username)

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
      django.contrib.messages.success(request, _("Login successful."))
      if django.utils.http.is_safe_url(url=d["next"], host=request.get_host()):
        return redirect(d["next"])
      else:
        return redirect("ui_home.index")
    else:
      django.contrib.messages.error(request, _("Login failed."))
      return uic.render(request, "account/login", d)
  else:
    return uic.methodNotAllowed(request)

def logout(request):
  """
  Logs the user out and redirects to the home page.
  """
  d = { 'menu_item' : 'ui_null.null'}
  if request.method != "GET": return uic.methodNotAllowed(request)
  request.session.flush()
  django.contrib.messages.success(request, _("You have been logged out."))
  return redirect("ui_home.index")

def _update_edit_user(request, user, new_proxies_selected, basic_info_changed):
  """method to update the user editing his/her information"""
  d = request.POST
  try:
    with django.db.transaction.atomic():
      user.primaryContactName = d["primaryContactName"]
      user.primaryContactEmail = d["primaryContactEmail"]
      user.primaryContactPhone = d["primaryContactPhone"]
      user.secondaryContactName = d["secondaryContactName"]
      user.secondaryContactEmail = d["secondaryContactEmail"]
      user.secondaryContactPhone = d["secondaryContactPhone"]
      user.displayName = d["accountDisplayName"]
      user.accountEmail = d["accountEmail"]
      user.proxies.clear()
      for p_user in [p_user.strip() for p_user in d["proxy_users_picked"].split(",")]:
        if p_user != "":
          user.proxies.add(ezidapp.models.getUserByUsername(p_user))
      if d["pwcurrent"].strip() != "": user.setPassword(d["pwnew"].strip())
      user.full_clean(validate_unique=False)
      user.save()
      ezidapp.admin.scheduleUserChangePostCommitActions(user)
  except django.core.validators.ValidationError, e:
    django.contrib.messages.error(request, str(e))
  else:
    if new_proxies_selected:
      for new_p in new_proxies_selected:
        _sendEmail(new_p, user)
    if basic_info_changed:
      django.contrib.messages.success(request,
        _("Your information has been updated."))
    if d['pwcurrent'].strip() != '' and d['pwnew'].strip() != '':
      django.contrib.messages.success(request, _("Your password has been updated."))

def _sendEmail (p_user, user):
  m = (_("Dear") + "%s,\n\n" +\
    _("You have been added as a proxy user to the identifiers owned by the following ") +\
    _("primary user") + ":\n\n" +\
    "   " + _("User") + ": %s\n" +\
    "   " + _("Username") + ": %s\n" +\
    "   " + _("Account") + ": %s\n" +\
    "   " + _("Account Email") + ": %s\n" +\
    _("As a proxy user, you can create and modify identifiers owned by the primary user") + ". " +\
    _("If you need more information about proxy ownership of EZID identifiers, ") +\
    _("please don't hesitate to contact us: http://ezid.cdlib.org/contact\n\n") +\
    _("Best,\nEZID Team\n\n\nThis is an automated email. Please do not reply.\n")) %\
    (p_user.primaryContactName, 
     user.primaryContactName, user.username, user.displayName, user.accountEmail)
  try:
    django.core.mail.send_mail(_("You've Been Added to an EZID Account"), m,
      django.conf.settings.SERVER_EMAIL, [p_user.accountEmail], fail_silently=True)
  except Exception, e:
    u = p_user.primaryContactName + "<" + p_user.accountEmail + ">"
    django.contrib.messages.error(request, "error sending email to " + u + ":" + e)


      
def pwreset(request, pwrr, ssl=False):
  """
  Handles all GET and POST interactions related to password resets.
  """
  if pwrr:  # Change password here after receiving email
    d = { 'menu_item' : 'ui_null.null'}
    r = decodePasswordResetRequest(pwrr)
    if not r:
      django.contrib.messages.error(request, _("Invalid password reset request."))
      return uic.redirect("/")
    username, t = r
    if int(time.time())-t >= 24*60*60:
      django.contrib.messages.error(request, _("Password reset request has expired."))
      return uic.redirect("/")
    d['pwrr'] = pwrr
    if request.method == "GET":
      d['username'] = username 
      d['form'] = form_objects.BasePasswordForm(None, username=username, pw_reqd=True)
    elif request.method == "POST":
      if "password" not in request.POST or "confirm" not in request.POST:
        return uic.badRequest()
      password = request.POST["password"]
      d['form'] = form_objects.BasePasswordForm(request.POST, username=username, pw_reqd=True)
      if not d['form'].is_valid():
        err = _("Changes could not be made.  Please check the highlighted field(s) below for details.")
        django.contrib.messages.error(request, err)
      else:
        user = ezidapp.models.getUserByUsername(username)
        if user == None or user.isAnonymous:
          django.contrib.messages.error(request, "No such user.")
          return uic.render(request, "account/pwreset2", { "pwrr": pwrr,
            "username": username, 'menu_item' : 'ui_null.null' })
        with django.db.transaction.atomic():
          user.setPassword(password)
          user.save()
          ezidapp.admin.scheduleUserChangePostCommitActions(user)
        django.contrib.messages.success(request, _("Password changed."))
        return uic.redirect("/")
    else:
      return uic.methodNotAllowed(request)
    return uic.render(request, "account/pwreset2", d) 
  else:
    # First step: enter your username and email to get sent an email containing link for password change
    d = { 'menu_item' : 'ui_null.null'}
    if request.method == "GET":
      d['form'] = form_objects.PwResetLandingForm()
      return uic.render(request, "account/pwreset1", d)
    elif request.method == "POST":
      P = request.POST
      if "username" not in P or "email" not in P:
        return uic.badRequest(request)
      username = P["username"].strip()
      email = P["email"].strip()
      d['form'] = form_objects.PwResetLandingForm(P)
      if not d['form'].is_valid():
        return uic.render(request, "account/pwreset1", d)
      else:
        r = sendPasswordResetEmail(username, email)
        if type(r) is str:
          django.contrib.messages.error(request, r)
          return uic.render(request, "account/pwreset1", { "username": username,
            "email": email,  'menu_item' : 'ui_null.null' })
        else:
          django.contrib.messages.success(request, _("Email sent."))
          return uic.redirect("/")
    else:
      return uic.methodNotAllowed(request)

def sendPasswordResetEmail (username, emailAddress):
  """
  Sends an email containing a password reset request link.  Returns
  None on success or a string message on error.
  """
  user = ezidapp.models.getUserByUsername(username)
  if user == None or user.isAnonymous: return _("No such user.")
  if emailAddress not in [user.accountEmail, user.primaryContactEmail,
    user.secondaryContactEmail]:
    return _("Email address does not match any address registered for username.")
  t = int(time.time())
  hash = hashlib.sha1("%s|%d|%s" % (username, t,
    django.conf.settings.SECRET_KEY)).hexdigest()[::4]
  link = "%s/account/pwreset/%s,%d,%s" %\
    (uic.ezidUrl, urllib.quote(username), t, hash)
  message = _("You have requested to reset your EZID password") + ".\n" +\
    _("Click the link below to complete the process") + ":\n\n" +\
    link + "\n\n" +\
    _("Please do not reply to this email") + ".\n"
  django.core.mail.send_mail(_("EZID password reset request"), message,
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
