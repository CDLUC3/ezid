import ui_common as uic
import django.contrib.messages
from django.shortcuts import redirect
import ezid
import urllib
import userauth

def index(request):
  """
  Renders the manage page (GET) or processes a manage form submission
  (POST).  A successful management request redirects to the
  identifier's view/management page.
  """
  d = { 'menu_item' : 'ui_lookup.index' }
  if request.method == "GET":
    return uic.render(request, 'lookup/index', d)
  elif request.method == "POST":
    if "identifier" not in request.POST: return uic.badRequest()
    id = request.POST["identifier"].strip()
    r = ezid.getMetadata(id, userauth.getUser(request, returnAnonymous=True))
    if type(r) is tuple:
      s, m = r
      assert s.startswith("success:")
      return redirect('/id/' + urllib.quote(s.split()[1], ":/"))
    else:
      django.contrib.messages.error(request, uic.formatError(r))
      return uic.render(request, "lookup/index", dict({ "identifier": id }.items() + d.items() ))
  else:
    return uic.methodNotAllowed()


