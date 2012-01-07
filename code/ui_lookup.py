import ui_common as uic
import django.contrib.messages
from django.shortcuts import redirect
import ezid
import metadata

d = { 'menu_item' : 'ui_lookup.null'}

def index(request):
  """
  Renders the manage page (GET) or processes a manage form submission
  (POST).  A successful management request redirects to the
  identifier's view/management page.
  """
  d['menu_item'] = 'ui_lookup.index'
  if request.method == "GET":
    return uic.render(request, 'lookup/index', d)
  elif request.method == "POST":
    if "identifier" not in request.POST: return uic.badRequest()
    id = request.POST["identifier"].strip()
    r = ezid.getMetadata(id)
    if type(r) is tuple:
      s, m = r
      assert s.startswith("success:")
      return redirect('ui_manage.details', s[8:].strip())
      #return redirect("/ezid/id/" + urllib.quote(s[8:].strip(), ":/"))
    else:
      django.contrib.messages.error(request, uic.formatError(r))
      return uic.render(request, "lookup/index", dict({ "identifier": id }.items() + d.items() ))
  else:
    return uic.methodNotAllowed()


