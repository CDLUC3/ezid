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
import datacite
import ezid
import ezidadmin
import idmap
import log
import metadata
import policy
import useradmin
import userauth

_ezidUrl = None
_templates = None
_alertMessage = None
_prefixes = None
_testPrefixes = None
_defaultDoiProfile = None
_defaultArkProfile = None
_defaultUrnUuidProfile = None
_adminUsername = None
_shoulders = None

def _loadConfig ():
  global _ezidUrl, _templates, _alertMessage, _prefixes, _testPrefixes
  global _defaultDoiProfile, _defaultArkProfile, _defaultUrnUuidProfile
  global _adminUsername, _shoulders
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
  _defaultDoiProfile = config.config("DEFAULT.default_doi_profile")
  _defaultArkProfile = config.config("DEFAULT.default_ark_profile")
  _defaultUrnUuidProfile = config.config("DEFAULT.default_urn_uuid_profile")
  _adminUsername = config.config("ldap.admin_username")
  _shoulders = [{ "label": k, "name": config.config("prefix_%s.name" % k),
    "prefix": config.config("prefix_%s.prefix" % k) }\
    for k in config.config("prefixes.keys").split(",")\
    if not k.startswith("TEST")]

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

def _staticHtmlResponse (content):
  r = django.http.HttpResponse(content,
    content_type="text/html; charset=UTF-8")
  r["Content-Length"] = len(content)
  return r

def _plainTextResponse (message):
  r = django.http.HttpResponse(message, content_type="text/plain")
  r["Content-Length"] = len(message)
  return r

# Our development version of Python (2.5) doesn't have the standard
# JSON module (introduced in 2.6), so we provide our own encoder here.

_jsonRe = re.compile("[\\x00-\\x1F\"\\\\\\xFF]")
def _json (o):
  if type(o) is dict:
    assert all(type(k) is str for k in o), "unexpected object type"
    return "{" + ", ".join(_json(k) + ": " + _json(v) for k, v in o.items()) +\
      "}"
  elif type(o) is list:
    return "[" + ", ".join(_json(v) for v in o) + "]"
  elif type(o) is str or type(o) is unicode:
    return "\"" + _jsonRe.sub(lambda c: "\\u%04X" % ord(c.group(0)), o) + "\""
  elif type(o) is bool:
    return "true" if o else "false"
  else:
    assert False, "unexpected object type"

def _jsonResponse (data):
  # Per RFC 4627, the default encoding is understood to be UTF-8.
  ec = _json(data).encode("UTF-8")
  r = django.http.HttpResponse(ec, content_type="application/json")
  r["Content-Length"] = len(ec)
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
    auth = userauth.authenticate(request.POST["username"],
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
      return _redirect("/ezid/")
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
      return _redirect("/ezid/id/" + urllib.quote(s.split()[1], ":/"))
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
  id = request.path[9:]
  if request.method == "GET":
    r = ezid.getMetadata(id)
    if type(r) is str:
      django.contrib.messages.error(request, _formatError(r))
      return _redirect("/ezid/manage")
    s, m = r
    if "_ezid_role" in m and ("auth" not in request.session or\
      request.session["auth"].user[0] != _adminUsername):
      # Special case.
      django.contrib.messages.error(request, "Unauthorized.")
      return _redirect("/ezid/manage")
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
      if int(time.time())-int(m["_created"]) < 1800:
        ip["_urlform"].note = "(takes up to 30 minutes for link to work)"
    elif id.startswith("ark:/") or id.startswith("urn:uuid:"):
      ip["_urlform"].value = "http://n2t.net/" + urllib.quote(id, ":/")
    else:
      ip["_urlform"].value = "(none)"
    if m["_status"].startswith("unavailable") and "|" in m["_status"]:
      ip["_status"].value = "unavailable (%s)" %\
        m["_status"].split("|", 1)[1].strip()
    if ip["_target"].value == defaultTargetUrl:
      ip["_target"].value = "(this page)"
    ip["_created"].value = _formatTime(int(ip["_created"].value))
    ip["_updated"].value = _formatTime(int(ip["_updated"].value))
    for f in ["_shadows", "_shadowedby"]:
      if ip[f].value != "(no value)":
        ip[f].hyperlink = "/ezid/id/" + urllib.quote(ip[f].value, ":/")
    if ip["_profile"].value not in [p.name for p in profiles[1:]]:
      if id.startswith("doi:"):
        ip["_profile"].value = _defaultDoiProfile
      elif id.startswith("urn:uuid:"):
        ip["_profile"].value = _defaultUrnUuidProfile
      else:
        ip["_profile"].value = _defaultArkProfile
    if ip["_coowners"].value == "(no value)": ip["_coowners"].value = "(none)"
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
    # Similar capability for the DataCite profile.
    dp = [p for p in profiles if p.name == "datacite"][0]
    if dp["datacite"].value != "(no value)":
      dp.elements = [e for e in dp.elements if e.name == "datacite"]
      html = datacite.dcmsRecordToHtml(dp["datacite"].value)
      if html is not None:
        dp["datacite"].value = html
        dp["datacite"].htmlMode = True
    else:
      dp.elements = [e for e in dp.elements if e.name != "datacite"]
    # Determine if the user can edit the metadata.
    if "auth" in request.session:
      user = request.session["auth"].user
      group = request.session["auth"].group
    else:
      user = group = ("anonymous", "anonymous")
    if ip["_coowners"].value == "(none)":
      coOwners = []
    else:
      coOwners = [(co.strip(), idmap.getUserId(co.strip()))\
        for co in ip["_coowners"].value.split(";") if len(co.strip()) > 0]
    editable = policy.authorizeUpdate(user, group, id,
      (ip["_owner"].value, idmap.getUserId(ip["_owner"].value)),
      (ip["_ownergroup"].value, idmap.getGroupId(ip["_ownergroup"].value)),
      coOwners, [])
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
      return _redirect("/ezid/id/" + urllib.quote(s.split()[1], ":/"))
    elif s.startswith("error: bad request - identifier already exists"):
      django.contrib.messages.error(request, _formatError(s))
      return _redirect("/ezid/id/" + urllib.quote(prefix+suffix, ":/"))
    else:
      django.contrib.messages.error(request, _formatError(s))
      return _render(request, "help", { "index": i, "suffix": suffix,
        "prefixes": _testPrefixes })
  else:
    return _methodNotAllowed()

def admin (request, ssl=False):
  """
  Renders the EZID admin page (GET) or processes a form submission on
  the admin page (POST).
  """
  global _alertMessage
  if "auth" not in request.session or\
    request.session["auth"].user[0] != _adminUsername:
    return _unauthorized()
  if request.method == "GET":
    return _render(request, "admin", { "shoulders": _shoulders })
  elif request.method == "POST":
    P = request.POST
    if "operation" not in P: return _badRequest()
    if P["operation"] == "make_group":
      if "gid" not in P: return _badRequest()
      r = ezidadmin.makeLdapGroup(P["gid"].strip())
      if type(r) is str: return _plainTextResponse(r)
      dn = r[0]
      r = ezidadmin.makeGroup(dn, P["gid"].strip(), False, "NONE",
        request.session["auth"].user, request.session["auth"].group)
      if type(r) is str:
        return _plainTextResponse(r)
      else:
        return _plainTextResponse("success: " + dn)
    elif P["operation"] == "update_group":
      if "dn" not in P or "description" not in P or\
        "agreementOnFile" not in P or\
        P["agreementOnFile"].lower() not in ["true", "false"] or\
        "shoulderList" not in P:
        return _badRequest()
      r = ezidadmin.updateGroup(P["dn"], P["description"].strip(),
        (P["agreementOnFile"].lower() == "true"), P["shoulderList"].strip(),
        request.session["auth"].user, request.session["auth"].group)
      if type(r) is str:
        return _plainTextResponse(r)
      else:
        return _plainTextResponse("success")
    elif P["operation"] == "make_user":
      if "uid" not in P or "existingLdapUser" not in P or "groupDn" not in P:
        return _badRequest()
      if P["existingLdapUser"].lower() == "false":
        r = ezidadmin.makeLdapUser(P["uid"].strip())
        if type(r) is str: return _plainTextResponse(r)
      r = ezidadmin.makeUser(P["uid"].strip(), P["groupDn"],
        request.session["auth"].user, request.session["auth"].group)
      if type(r) is str:
        return _plainTextResponse(r)
      else:
        return _plainTextResponse("success: " + r[0])
    elif P["operation"] == "update_user":
      for a in ["uid", "ezidCoOwners", "disable", "userPassword"]:
        if a not in P: return _badRequest()
      d = {}
      for a in ["givenName", "sn", "mail", "telephoneNumber", "description"]:
        if a not in P: return _badRequest()
        d[a] = P[a].strip()
      if d["sn"] == "": return _plainTextResponse("Last name is required.")
      if d["mail"] == "":
        return _plainTextResponse("Email address is required.")
      r = useradmin.setContactInfo(P["uid"], d)
      if type(r) is str: return _plainTextResponse(r)
      r = useradmin.setAccountProfile(P["uid"], P["ezidCoOwners"].strip())
      if type(r) is str: return _plainTextResponse(r)
      if P["disable"].lower() == "true":
        r = ezidadmin.disableUser(P["uid"])
        if type(r) is str: return _plainTextResponse(r)
      elif P["userPassword"].strip() != "":
        r = useradmin.resetPassword(P["uid"], P["userPassword"].strip())
        if type(r) is str: return _plainTextResponse(r)
      return _plainTextResponse("success")
    elif P["operation"] == "set_alert":
      if "message" not in P: return _badRequest()
      m = P["message"].strip()
      f = open(os.path.join(django.conf.settings.SITE_ROOT, "db",
        "alert_message"), "w")
      f.write(m)
      f.close()
      _alertMessage = m
      return _render(request, "admin", { "shoulders": _shoulders })
    elif P["operation"] == "reload":
      config.load()
      request.session.flush()
      django.contrib.messages.success(request, "EZID reloaded.")
      django.contrib.messages.success(request, "You have been logged out.")
      return _redirect("/ezid/")
    else:
      return _badRequest()
  else:
    return _methodNotAllowed()

def getEntries (request):
  """
  Returns all LDAP entries.
  """
  if "auth" not in request.session or\
    request.session["auth"].user[0] != _adminUsername:
    return _unauthorized()
  if request.method != "GET": return _methodNotAllowed()
  return _jsonResponse(ezidadmin.getEntries("usersOnly" in request.GET and\
    request.GET["usersOnly"].lower() == "true",
    "nonEzidUsersOnly" in request.GET and\
    request.GET["nonEzidUsersOnly"].lower() == "true"))

def getGroups (request):
  """
  Returns all EZID groups.
  """
  if "auth" not in request.session or\
    request.session["auth"].user[0] != _adminUsername:
    return _unauthorized()
  if request.method != "GET": return _methodNotAllowed()
  return _jsonResponse(ezidadmin.getGroups())

def getUsers (request):
  """
  Returns all EZID users.
  """
  if "auth" not in request.session or\
    request.session["auth"].user[0] != _adminUsername:
    return _unauthorized()
  if request.method != "GET": return _methodNotAllowed()
  return _jsonResponse(ezidadmin.getUsers())

def systemStatus (request):
  """
  AJAX support.  In response to a GET request, returns a plain text
  subsystem status (if an 'id' parameter is supplied) or a JSON list
  of subsystems (if not).
  """
  if "auth" not in request.session or\
    request.session["auth"].user[0] != _adminUsername:
    return _unauthorized()
  if request.method != "GET": return _methodNotAllowed()
  if "id" in request.GET:
    return _plainTextResponse(ezidadmin.systemStatus(request.GET["id"]))
  else:
    return _jsonResponse(ezidadmin.systemStatus())

def resetPassword (request, pwrr, ssl=False):
  """
  Handles all GET and POST interactions related to password resets.
  """
  if pwrr:
    r = useradmin.decodePasswordResetRequest(pwrr)
    if not r:
      django.contrib.messages.error(request, "Invalid password reset request.")
      return _redirect("/ezid/")
    username, t = r
    if int(time.time())-t >= 24*60*60:
      django.contrib.messages.error(request,
        "Password reset request has expired.")
      return _redirect("/ezid/")
    if request.method == "GET":
      return _render(request, "pwreset2", { "pwrr": pwrr,
        "username": username })
    elif request.method == "POST":
      if "password" not in request.POST or "confirm" not in request.POST:
        return _badRequest()
      password = request.POST["password"]
      confirm = request.POST["confirm"]
      if password != confirm:
        django.contrib.messages.error(request,
          "Password and confirmation do not match.")
        return _render(request, "pwreset2", { "pwrr": pwrr,
          "username": username })
      if password == "":
        django.contrib.messages.error(request, "Password required.")
        return _render(request, "pwreset2", { "pwrr": pwrr,
          "username": username })
      r = useradmin.resetPassword(username, password)
      if type(r) is str:
        django.contrib.messages.error(request, r)
        return _render(request, "pwreset2", { "pwrr": pwrr,
          "username": username })
      else:
        django.contrib.messages.success(request, "Password changed.")
        return _redirect("/ezid/")
    else:
      return _methodNotAllowed()
  else:
    if request.method == "GET":
      return _render(request, "pwreset1")
    elif request.method == "POST":
      if "username" not in request.POST or "email" not in request.POST:
        return _badRequest()
      username = request.POST["username"].strip()
      email = request.POST["email"].strip()
      if username == "":
        django.contrib.messages.error(request, "Username required.")
        return _render(request, "pwreset1", { "email": email })
      if email == "":
        django.contrib.messages.error(request, "Email address required.")
        return _render(request, "pwreset1", { "username": username })
      r = useradmin.sendPasswordResetEmail(username, email)
      if type(r) is str:
        django.contrib.messages.error(request, r)
        return _render(request, "pwreset1", { "username": username,
          "email": email })
      else:
        django.contrib.messages.success(request, "Email sent.")
        return _redirect("/ezid/")
    else:
      return _methodNotAllowed()

_contactInfoFields = [
  ("givenName", "First name", False),
  ("sn", "Last name", True),
  ("mail", "Email address", True),
  ("telephoneNumber", "Phone number", False)]

def account (request, ssl=False):
  """
  Renders the user account page (GET) or processes an AJAX form
  submission on the user account page (POST).
  """
  if "auth" not in request.session: return _unauthorized()
  if request.method == "GET":
    r = useradmin.getAccountProfile(request.session["auth"].user[0])
    if type(r) is str:
      django.contrib.messages.error(request, r)
      return _redirect("/ezid/")
    r2 = useradmin.getContactInfo(request.session["auth"].user[0])
    if type(r2) is str:
      django.contrib.messages.error(request, r2)
      return _redirect("/ezid/")
    r.update(r2)
    return _render(request, "account", r)
  elif request.method == "POST":
    if request.POST.get("form", "") == "profile":
      if "ezidCoOwners" not in request.POST: return _badRequest()
      r = useradmin.setAccountProfile(request.session["auth"].user[0],
        request.POST["ezidCoOwners"].strip())
      if type(r) is str:
        return _plainTextResponse(r)
      else:
        return _plainTextResponse("success")
    elif request.POST.get("form", "") == "contact":
      d = {}
      missing = None
      for field, displayName, isRequired in _contactInfoFields:
        if field not in request.POST: return _badRequest()
        d[field] = request.POST[field].strip()
        if isRequired and d[field] == "": missing = displayName
      if missing: return _plainTextResponse(missing + " is required.")
      r = useradmin.setContactInfo(request.session["auth"].user[0], d)
      if type(r) is str:
        return _plainTextResponse(r)
      else:
        return _plainTextResponse("success")
    elif request.POST.get("form", "") == "password":
      if "pwcurrent" not in request.POST or "pwnew" not in request.POST:
        return _badRequest()
      if request.POST["pwcurrent"] == "":
        return _plainTextResponse("Current password required.")
      if request.POST["pwnew"] == "":
        return _plainTextResponse("New password required.")
      r = useradmin.setPassword(request.session["auth"].user[0],
        request.POST["pwcurrent"], request.POST["pwnew"])
      if type(r) is str:
        return _plainTextResponse(r)
      else:
        return _plainTextResponse("success")
    else:
      return _badRequest()
  else:
    return _methodNotAllowed()

def doc (request):
  """
  Renders UTF-8 encoded HTML documentation.
  """
  if request.method != "GET": return _methodNotAllowed()
  assert request.path.startswith("/ezid/doc/")
  file = os.path.join(django.conf.settings.PROJECT_ROOT, "doc",
    request.path[10:])
  if os.path.exists(file):
    f = open(file)
    content = f.read()
    f.close()
    # If the filename of the requested document has what looks to be a
    # version indicator, attempt to load the unversioned (i.e.,
    # latest) version of the document.  Then, if the requested
    # document is not the latest version, add a warning.
    m = re.match("(.*/\w+)\.\w+\.html$", file)
    if m:
      uvfile = m.group(1) + ".html"
      if os.path.exists(uvfile):
        f = open(uvfile)
        uvcontent = f.read()
        f.close()
        if content != uvcontent:
          content = re.sub("<!-- superseded warning placeholder -->",
            "<p class='warning'>THIS VERSION IS SUPERSEDED BY A NEWER " +\
            "VERSION</p>", content)
    return _staticHtmlResponse(content)
  else:
    return _error(404)

def tombstone (request):
  """
  Renders a tombstone (i.e., unavailable identifier) page.
  """
  if request.method != "GET": return _methodNotAllowed()
  assert request.path.startswith("/ezid/tombstone/id/")
  id = request.path[19:]
  r = ezid.getMetadata(id)
  if type(r) is str:
    django.contrib.messages.error(request, _formatError(r))
    return _redirect("/ezid/")
  s, m = r
  if "_ezid_role" in m and ("auth" not in request.session or\
    request.session["auth"].user[0] != _adminUsername):
    # Special case.
    django.contrib.messages.error(request, "Unauthorized.")
    return _redirect("/ezid/")
  assert s.startswith("success:")
  id = s[8:].strip()
  if not m["_status"].startswith("unavailable"):
    return _redirect("/ezid/id/%s" % urllib.quote(id, ":/"))
  if "|" in m["_status"]:
    reason = "Not available: " + m["_status"].split("|", 1)[1].strip()
  else:
    reason = "Not available"
  htmlMode = False
  if m["_profile"] == "datacite" and "datacite" in m:
    md = datacite.dcmsRecordToHtml(m["datacite"])
    if md: htmlMode = True
  if not htmlMode:
    # This echoes the Merritt hack above.
    if m["_profile"] == "erc" and m.get("erc", "").strip() != "":
      md = [{ "label": "ERC", "value": m["erc"].strip() }]
    else:
      p = metadata.getProfile(m["_profile"])
      if not p: p = metadata.getProfile("erc")
      md = []
      for e in p.elements:
        if "." not in e.name: continue
        v = m.get(e.name, "").strip()
        md.append({ "label": e.displayName,
          "value": v if v != "" else "(no value)" })
  return _render(request, "tombstone", { "identifier": id,
    "identifierLink": "/ezid/id/%s" % urllib.quote(id, ":/"),
    "reason": reason, "htmlMode": htmlMode, "metadata": md })
