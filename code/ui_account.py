import ui_common as uic
import userauth, useradmin
import django.contrib.messages
import form_objects
import re
import time
from django.shortcuts import redirect
from django.utils.translation import ugettext as _

# Temporary, for testing
proxy_users_mock = {'ucsd_signaling_gateway': 'Center for International Earth Science Information Network (CIESIN)', 
'aasdata': 'ESIPCommon Federation of Earth Science Information Partners (ESIP) Commons', 
'acsess': 'Indiana University Sustainable Environment-Actionable Data (SEAD)', 
'aep': 'Laboratory for Basic and Translational Cognitive Neuroscience', 
'artlas': 'Partnership for Interdisciplinary Studies of Coastal Oceans (PISCO)', 
'ualberta': 'UAlberta Journal of Professional Continuing and Online Education', 
'benchfly': 'Center for International Earth Science Information Network (CIESIN)', 
'biocaddie': 'ESIPCommon Federation of Earth Science Information Partners (ESIP) Commons', 
'biocaddie-api': 'Indiana University Sustainable Environment-Actionable Data (SEAD)'}
proxy_users_mock_picked = "aasdata, acsess"

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
  if request.method == "GET":
    d['proxy_users_picked'] = proxy_users_mock_picked
    d['proxy_users'] = proxy_users_mock
    d['form'] = form_objects.UserForm(d, username=d['username'], pw_reqd=False)
  else:
    # ToDo: Email new proxy users 
    d['form'] = form_objects.UserForm(request.POST, initial=d, username=d['username'], pw_reqd=False)
    basic_info_changed=False
    if d['form'].is_valid():
      if d['form'].has_changed():
        basic_info_changed = any(ch in d['form'].changed_data for ch in \
          ['givenName', 'sn', 'telephoneNumber', 'mail', 'proxy_users_picked'])
      _update_edit_user(request, basic_info_changed)
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
      django.contrib.messages.success(request, _("Login successful."))
      #request.session['hide_alert'] = False
      if 'redirect_to' in request.POST:
        return redirect(_filterBadRedirect(request.POST['redirect_to']))
      if 'redirect_to' in request.session and request.session['redirect_to']:
        return redirect(_filterBadRedirect(request.session['redirect_to']))
      else:
        return redirect('ui_home.index')
    else:
      django.contrib.messages.error(request, _("Login failed."))
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
  django.contrib.messages.success(request, _("You have been logged out."))
  return redirect("ui_home.index")

def _update_edit_user(request, basic_info_changed):
  """
  Method to update the user editing his/her information.
  """
  uid = request.session['auth'].user[0]
  di = {}
  P = request.POST
  for item in ['givenName', 'sn', 'mail', 'telephoneNumber']:
    di[item] = P[item].strip()
  r = useradmin.setContactInfo(uid, di)
  if type(r) is str: django.contrib.messages.error(request, r)
  # ToDo: Change to proxy users
  # if P['ezidCoOwners'].strip() == '':
  #  r = useradmin.setAccountProfile(uid, '')
  # else:
  #   r = useradmin.setAccountProfile(uid, P['ezidCoOwners'].strip())
  if type(r) is str:
    django.contrib.messages.error(request, r)
  else:
    if basic_info_changed: django.contrib.messages.success(request,
      _("Your information has been updated."))
  
  if P['pwcurrent'].strip() != '' and P['pwnew'].strip() != '':
    r = useradmin.resetPassword(uid, P["pwnew"].strip())
    if type(r) is str:
      django.contrib.messages.error(request, r)
    else:
      django.contrib.messages.success(request, _("Your password has been updated."))
      
def pwreset(request, pwrr, ssl=False):
  """
  Handles all GET and POST interactions related to password resets.
  """
  if pwrr:  # Change password here after receiving email
    d = { 'menu_item' : 'ui_null.null'}
    r = useradmin.decodePasswordResetRequest(pwrr)
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
      d['form'] = form_objects.BasePasswordForm(request.POST, username=username, pw_reqd=True)
      if not d['form'].is_valid():
        err = _("Changes could not be made.  Please check the highlighted field(s) below for details.")
        django.contrib.messages.error(request, err)
      else:
        r = useradmin.resetPassword(username, d['form']['pwnew'].data)
        if type(r) is str:
          django.contrib.messages.error(request, r)
        else:
          django.contrib.messages.success(request, _("Password changed."))
          return uic.redirect("/")
    else:
      return uic.methodNotAllowed(request)
    return uic.render(request, "account/pwreset2", d) 
  else:
    # First step: enter your username and email to get sent an email contiaing link for password change
    d = { 'menu_item' : 'ui_null.null'}
    if request.method == "GET":
      d['form'] = form_objects.PwResetLandingForm()
      return uic.render(request, "account/pwreset1", d)
    elif request.method == "POST":
      P = request.POST
      if "username" not in P or "email" not in P:
        return uic.badRequest(request)
      d['form'] = form_objects.PwResetLandingForm(P)
      if d['form'].is_valid():
        r = useradmin.sendPasswordResetEmail(P['username'], P['email'])
        if type(r) is str:
          django.contrib.messages.error(request, r)
          return uic.render(request, "account/pwreset1", d)
        else:
          django.contrib.messages.success(request, _("Email sent."))
          return uic.redirect("/")
      return uic.render(request, "account/pwreset1", d)
    else:
      return uic.methodNotAllowed(request)
