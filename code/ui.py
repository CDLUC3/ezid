# =============================================================================
#
# EZID :: ui.py
#
# User interface.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2010, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.conf
import django.contrib.messages
import django.http
import django.template
import django.template.loader
import errno
import os
import re
import time
import urllib

import config
import ezid
import log
import metadata
import policy
import userauth

_ezidUrl = None
_templates = None
_alertMessage = None
_prefixes = None
_testPrefixes = None
_testDoiPrefix = None
_defaultDoiProfile = None
_defaultArkProfile = None
_adminUsername = None

def _loadConfig ():
  global _ezidUrl, _templates, _alertMessage, _prefixes, _testPrefixes
  global _testDoiPrefix, _defaultDoiProfile, _defaultArkProfile, _adminUsername
  _ezidUrl = config.config("DEFAULT.ezid_base_url")
  t = {}
  for f in os.listdir(django.conf.settings.TEMPLATE_DIRS[0]):
    if f.endswith(".html"): t[f[:-5]] = django.template.loader.get_template(f)
  _templates = t
  try:
    f = open(os.path.join(django.conf.settings.SITE_ROOT, "db",
      "alert_message"))
    _alertMessage = f.read().strip()
    f.close()
  except IOError, e:
    if e.errno == errno.ENOENT:
      _alertMessage = ""
    else:
      raise
  keys = config.config("prefixes.keys").split(",")
  _prefixes = dict([config.config("prefix_%s.prefix" % k),
    config.config("prefix_%s.name" % k)] for k in keys)
  _testPrefixes = [{ "namespace": config.config("prefix_%s.name" % k),
    "prefix": config.config("prefix_%s.prefix" % k) }\
    for k in keys if k.startswith("TEST")]
  _testDoiPrefix = config.config("prefix_TESTDOI.prefix")
  _defaultDoiProfile = config.config("DEFAULT.default_doi_profile")
  _defaultArkProfile = config.config("DEFAULT.default_ark_profile")
  _adminUsername = config.config("ldap.admin_username")

_loadConfig()
config.addLoader(_loadConfig)

def _render (request, template, context={}):
  c = { "session": request.session, "alertMessage": _alertMessage }
  c.update(context)
  content = _templates[template].render(
    django.template.RequestContext(request, c))
  # By setting the content type ourselves, we gain control over the
  # character encoding and can properly set the content length.
  ec = content.encode("UTF-8")
  r = django.http.HttpResponse(ec, content_type="text/html; charset=UTF-8")
  r["Content-Length"] = len(ec)
  return r

def _plainTextResponse (message):
  r = django.http.HttpResponse(message, content_type="text/plain")
  r["Content-Length"] = len(message)
  return r

_redirect = django.http.HttpResponseRedirect

def _error (code):
  content = _templates[str(code)].render(django.template.Context())
  return django.http.HttpResponse(content, status=code)

def _badRequest ():
  return _error(400)

def _unauthorized ():
  return _error(401)

def _methodNotAllowed ():
  return _error(405)

def _formatError (message):
  for p in ["error: bad request - ", "error: "]:
    if message.startswith(p) and len(message) > len(p):
      return message[len(p)].upper() + message[len(p)+1:] + "."
  return message

def _getPrefixes (user, group):
  try:
    return [{ "namespace": _prefixes.get(p, "?"), "prefix": p }\
      for p in policy.getPrefixes(user, group)]
  except Exception, e:
    log.otherError("ui._getPrefixes", e)
    return "error: internal server error"

def login (request):
  """
  Renders the login page (GET) or processes a login form submission
  (POST).  A successful login redirects to the home page.
  """
  if request.method == "GET":
    return _render(request, "login")
  elif request.method == "POST":
    if "username" not in request.POST or "password" not in request.POST:
      return _badRequest()
    auth = userauth.authenticate(request.POST["username"].strip(),
      request.POST["password"])
    if type(auth) is str:
      django.contrib.messages.error(request, _formatError(auth))
      return _render(request, "login")
    if auth:
      p = _getPrefixes(auth.user, auth.group)
      if type(p) is str:
        django.contrib.messages.error(request, _formatError(p))
        return _render(request, "login")
      request.session["auth"] = auth
      request.session["prefixes"] = p
      django.contrib.messages.success(request, "Login successful.")
      u = request.build_absolute_uri()
      if u.startswith("https:"): u = "http:" + u[6:]
      assert u.endswith("/login")
      return _redirect(u[:-5])
    else:
      django.contrib.messages.error(request, "Login failed.")
      return _render(request, "login")
  else:
    return _methodNotAllowed()

def logout (request):
  """
  Logs the user out and redirects to the home page.
  """
  if request.method != "GET": return _methodNotAllowed()
  request.session.flush()
  django.contrib.messages.success(request, "You have been logged out.")
  return _redirect("/ezid/")

def clearHistory (request):
  """
  Clears the recent identifier list.
  """
  if request.method != "GET": return _methodNotAllowed()
  request.session["history"] = []
  return _plainTextResponse("success")

def home (request):
  """
  Renders the EZID home page.
  """
  if request.method != "GET": return _methodNotAllowed()
  return _render(request, "home")

def create (request):
  """
  Renders the create page (GET) or processes a create form submission
  (POST).  A successful creation redirects to the new identifier's
  view/management page.
  """
  if request.method == "GET":
    return _render(request, "create", { "index": 1 })
  elif request.method == "POST":
    if "auth" not in request.session:
      django.contrib.messages.error(request, "Unauthorized.")
      return _render(request, "create", { "index": 1 })
    P = request.POST
    if "index" not in P or not re.match("\d+$", P["index"]):
      return _badRequest()
    i = int(P["index"])
    if "prefix"+str(i) not in P or "suffix"+str(i) not in P:
      return _badRequest()
    prefix = P["prefix"+str(i)]
    suffix = P["suffix"+str(i)].strip()
    if suffix == "":
      s = ezid.mintIdentifier(prefix, request.session["auth"].user,
        request.session["auth"].group)
    else:
      s = ezid.createIdentifier(prefix+suffix, request.session["auth"].user,
        request.session["auth"].group)
    if s.startswith("success:"):
      django.contrib.messages.success(request, "Identifier created.")
      return _redirect("/ezid/id/" + urllib.quote(s[8:].strip(), ":/"))
    elif s.startswith("error: bad request - identifier already exists"):
      django.contrib.messages.error(request, _formatError(s))
      return _redirect("/ezid/id/" + urllib.quote(prefix+suffix, ":/"))
    else:
      django.contrib.messages.error(request, _formatError(s))
      return _render(request, "create", { "index": i, "suffix": suffix })
  else:
    return _methodNotAllowed()

def manage (request):
  """
  Renders the manage page (GET) or processes a manage form submission
  (POST).  A successful management request redirects to the
  identifier's view/management page.
  """
  if request.method == "GET":
    return _render(request, "manage")
  elif request.method == "POST":
    if "identifier" not in request.POST: return _badRequest()
    id = request.POST["identifier"].strip()
    r = ezid.getMetadata(id)
    if type(r) is tuple:
      s, m = r
      assert s.startswith("success:")
      return _redirect("/ezid/id/" + urllib.quote(s[8:].strip(), ":/"))
    else:
      django.contrib.messages.error(request, _formatError(r))
      return _render(request, "manage", { "identifier": id })
  else:
    return _methodNotAllowed()

def _formatTime (t):
  return time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime(t))

def _abbreviateIdentifier (id):
  if len(id) > 50:
    return id[:20] + " ... " + id[-20:]
  else:
    return id

def identifierDispatcher (request):
  """
  Renders an identifier's view/management page (GET) or processes an
  AJAX metadata update request (POST).
  """
  assert request.path.startswith("/ezid/id/")
  id = urllib.unquote(request.path[9:])
  if request.method == "GET":
    r = ezid.getMetadata(id)
    if type(r) is str:
      django.contrib.messages.error(request, _formatError(r))
      return _redirect("/ezid/manage")
    s, m = r
    assert s.startswith("success:")
    id = s[8:].strip()
    defaultTargetUrl = "%s/id/%s" % (_ezidUrl, urllib.quote(id, ":/"))
    # The display is oriented around metadata profiles, so instead of
    # iterating over whatever metadata elements are bound to the
    # identifier, we iterate over and fill in profile elements.
    profiles = metadata.getProfiles()
    for p in profiles:
      for e in p.elements:
        v = m.get(e.name, "").strip()
        if v != "":
          e.value = v
        else:
          e.value = "(no value)"
    assert profiles[0].name == "internal"
    ip = profiles[0]
    # The internal profile requires lots of customization.
    if id.startswith("doi:"):
      ip["_urlform"].value = "http://dx.doi.org/" + urllib.quote(id[4:], ":/")
      if id.startswith(_testDoiPrefix):
        ip["_urlform"].note = "(test identifier; link will not work)"
      elif int(time.time())-int(m["_created"]) < 1800:
        ip["_urlform"].note = "(may take 30 minutes for link to work)"
    elif id.startswith("ark:/"):
      ip["_urlform"].value = "http://n2t.net/" + urllib.quote(id, ":/")
    else:
      ip["_urlform"].value = "(none)"
    if ip["_target"].value == defaultTargetUrl:
      ip["_target"].value = "(this page)"
    for f in ["_owner", "_ownergroup"]:
      ip[f].fullValue = tuple(ip[f].value.split())
      ip[f].value = ip[f].fullValue[0]
    ip["_created"].value = _formatTime(int(ip["_created"].value))
    ip["_updated"].value = _formatTime(int(ip["_updated"].value))
    for f in ["_shadows", "_shadowedby"]:
      if ip[f].value != "(no value)":
        ip[f].hyperlink = "/ezid/id/" + urllib.quote(ip[f].value, ":/")
    if ip["_profile"].value not in [p.name for p in profiles[1:]]:
      if id.startswith("doi:"):
        ip["_profile"].value = _defaultDoiProfile
      else:
        ip["_profile"].value = _defaultArkProfile
    # Hack (hopefully temporary) for the Merritt folks.  In addition
    # to defining individual ERC fields, the ERC profile defines an
    # "erc" element to hold an entire block of ERC metadata.  We
    # display either the block or the individual fields, not both.
    # The "erc" element should be removed as soon as EZID has the
    # capability of displaying repeated elements.
    ep = [p for p in profiles if p.name == "erc"][0]
    if ep["erc"].value != "(no value)":
      ep.elements = [e for e in ep.elements if e.name == "erc"]
    else:
      ep.elements = [e for e in ep.elements if e.name != "erc"]
    # Determine if the user can edit the metadata.
    if "auth" in request.session:
      user = request.session["auth"].user
      group = request.session["auth"].group
    else:
      user = group = ("anonymous", "anonymous")
    editable = policy.authorizeUpdate(user, group, id, ip["_owner"].fullValue,
      ip["_ownergroup"].fullValue)
    # Update the recent identifier list.
    if "history" not in request.session: request.session["history"] = []
    if id not in [e["id"] for e in request.session["history"]]:
      request.session["history"].append({ "id": id,
        "url": "/ezid/id/" + urllib.quote(id, ":/"),
        "abbreviated": _abbreviateIdentifier(id) })
      request.session.modified = True
    # Finally!:
    return _render(request, "identifier", { "identifier": id,
      "defaultTargetUrl": defaultTargetUrl, "profiles": profiles,
      "editable": editable })
  elif request.method == "POST":
    if "auth" in request.session:
      user = request.session["auth"].user
      group = request.session["auth"].group
    else:
      user = group = ("anonymous", "anonymous")
    if "field" not in request.POST or "value" not in request.POST or\
      "profile" not in request.POST:
      return _plainTextResponse("Bad request.")
    s = ezid.setMetadata(id, user, group,
      { request.POST["field"]: request.POST["value"],
      "_profile": request.POST["profile"] })
    if s.startswith("success:"):
      s = "success"
    else:
      s = _formatError(s)
    return _plainTextResponse(s)
  else:
    return _methodNotAllowed()

def help (request):
  """
  Renders the help page (GET) or processes a create form submission on
  the help page (POST).  A successful creation redirects to the new
  identifier's view/management page.
  """
  if request.method == "GET":
    return _render(request, "help", { "index": 1, "prefixes": _testPrefixes })
  elif request.method == "POST":
    if "auth" in request.session:
      user = request.session["auth"].user
      group = request.session["auth"].group
    else:
      user = group = ("anonymous", "anonymous")
    P = request.POST
    if "index" not in P or not re.match("\d+$", P["index"]):
      return _badRequest()
    i = int(P["index"])
    if "prefix"+str(i) not in P or "suffix"+str(i) not in P:
      return _badRequest()
    prefix = P["prefix"+str(i)]
    suffix = P["suffix"+str(i)].strip()
    if suffix == "":
      s = ezid.mintIdentifier(prefix, user, group)
    else:
      s = ezid.createIdentifier(prefix+suffix, user, group)
    if s.startswith("success:"):
      django.contrib.messages.success(request, "Identifier created.")
      return _redirect("/ezid/id/" + urllib.quote(s[8:].strip(), ":/"))
    elif s.startswith("error: bad request - identifier already exists"):
      django.contrib.messages.error(request, _formatError(s))
      return _redirect("/ezid/id/" + urllib.quote(prefix+suffix, ":/"))
    else:
      django.contrib.messages.error(request, _formatError(s))
      return _render(request, "help", { "index": i, "suffix": suffix,
        "prefixes": _testPrefixes })
  else:
    return _methodNotAllowed()

def admin (request):
  """
  Renders the EZID admin page (GET) or processes a form submission on
  the admin page (POST).
  """
  global _alertMessage
  if "auth" not in request.session or\
    request.session["auth"].user[0] != _adminUsername:
    return _unauthorized()
  if request.method == "GET":
    return _render(request, "admin")
  elif request.method == "POST":
    P = request.POST
    if "operation" not in P: return _badRequest()
    if P["operation"] == "set_alert":
      if "message" not in P: return _badRequest()
      m = P["message"].strip()
      f = open(os.path.join(django.conf.settings.SITE_ROOT, "db",
        "alert_message"), "w")
      f.write(m)
      f.close()
      _alertMessage = m
      return _render(request, "admin")
    else:
      return _badRequest()
  else:
    return _methodNotAllowed()
