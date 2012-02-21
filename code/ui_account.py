import ui_common as uic
import userauth, useradmin
import django.contrib.messages
import idmap
from django.shortcuts import redirect

d = { 'menu_item' : 'ui_null.null'}

def edit(request):
  """Edit account information form"""
  if "auth" not in request.session: return uic.unauthorized()
  d['username'] = request.session['auth'].user[0]
  
  if request.method == "GET":
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
      
  elif request.method == "POST":
    if validate_edit_user(request):
      print "This would now save the form."
  return uic.render(request, "account/edit", d)

def login(request):
  """
  Renders the login page (GET) or processes a login form submission
  (POST).  A successful login redirects to the home page.
  """
  if request.method == "GET":
    return uic.render(request, 'account/login', d)
  elif request.method == "POST":
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
  if request.method != "GET": return uic.methodNotAllowed()
  request.session.flush()
  django.contrib.messages.success(request, "You have been logged out.")
  return redirect("ui_home.index")

def contact(request):
  pass


def validate_edit_user(request):
  """validates that the fields required to update a user are set"""
  valid_form = True
  fields = ['givenName', 'sn', 'mail', 'telephoneNumber', 'ezidCoOwners', 'pwcurrent','pwnew', 'pwconfirm']
  
  for field in fields:
    if not field in request.POST:
      django.contrib.messages.error(request, "Form submission error.")
      return False
  
  required_fields = {'givenName': 'First name', 'sn': 'Last name', 'mail': 'Email address'}
  for field in required_fields:
    if request.POST[field].strip() == '':
      django.contrib.messages.error(request, required_fields[field] + " must be filled in.")
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
      django.contrib.messages.error(request, "Your new and confirmed new passwords do not match.")
      valid_form = False
    if request.POST['pwnew'] == '' or request.POST['pwconfirm'] == '':
      django.contrib.messages.error(request, "Your new password cannot be empty.")
      valid_form = False
  return valid_form
  
  