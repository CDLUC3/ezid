import ui_common as uic
import userauth
import django.contrib.messages
from django.shortcuts import redirect

d = { 'menu_item' : 'ui_null.null'}

def edit(request):
  pass

def login(request):
  """
  Renders the login page (GET) or processes a login form submission
  (POST).  A successful login redirects to the home page.
  """
  if request.method == "GET":
    return uic.render(request, 'account/login', d)
  elif request.method == "POST":
    print "line 18"
    if "username" not in request.POST or "password" not in request.POST:
      return uic.badRequest()
    print "line 21"
    auth = userauth.authenticate(request.POST["username"],
      request.POST["password"])
    if type(auth) is str:
      print "line 25"
      django.contrib.messages.error(request, uic.formatError(auth))
      return uic.render(request, 'account/login', d)
    if auth:
      print "line 29"
      p = uic.getPrefixes(auth.user, auth.group)
      if type(p) is str:
        print "line 32"
        django.contrib.messages.error(request, uic.formatError(p))
        return uic.render(request, 'account/login', d)
      request.session["auth"] = auth
      request.session["prefixes"] = p
      django.contrib.messages.success(request, "Login successful.")
      print "line 38"
      return redirect('ui_home.index')
    else:
      print "line 41"
      django.contrib.messages.error(request, "Login failed.")
      return uic.render(request, "account/login", d)
  else:
    print "line 45"
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