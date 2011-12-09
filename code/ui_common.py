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

ezidUrl = None
templates = None
alertMessage = None
prefixes = None
testPrefixes = None
defaultDoiProfile = None
defaultArkProfile = None
defaultUrnUuidProfile = None
adminUsername = None
shoulders = None

def loadConfig():
  global ezidUrl, templates, alertMessage, prefixes, testPrefixes
  global defaultDoiProfile, defaultArkProfile, defaultUrnUuidProfile
  global adminUsername, shoulders
  ezidUrl = config.config("DEFAULT.ezid_base_url")
  t = {}
  for f in os.listdir(django.conf.settings.TEMPLATE_DIRS[0]):
    if f.endswith(".html"): t[f[:-5]] = django.template.loader.get_template(f)
  templates = t
  try:
    f = open(os.path.join(django.conf.settings.SITE_ROOT, "db",
      "alert_message"))
    alertMessage = f.read().strip()
    f.close()
  except IOError, e:
    if e.errno == errno.ENOENT:
      alertMessage = ""
    else:
      raise
  keys = config.config("prefixes.keys").split(",")
  prefixes = dict([config.config("prefix_%s.prefix" % k),
    config.config("prefix_%s.name" % k)] for k in keys)
  testPrefixes = [{ "namespace": config.config("prefix_%s.name" % k),
    "prefix": config.config("prefix_%s.prefix" % k) }\
    for k in keys if k.startswith("TEST")]
  defaultDoiProfile = config.config("DEFAULT.default_doi_profile")
  defaultArkProfile = config.config("DEFAULT.default_ark_profile")
  defaultUrnUuidProfile = config.config("DEFAULT.default_urn_uuid_profile")
  adminUsername = config.config("ldap.admin_username")
  shoulders = [{ "label": k, "name": config.config("prefix_%s.name" % k),
    "prefix": config.config("prefix_%s.prefix" % k) }\
    for k in config.config("prefixes.keys").split(",")\
    if not k.startswith("TEST")]

def render (request, template, context={}):
  c = { "session": request.session, "alertMessage": alertMessage }
  c.update(context)
  content = templates[template].render(
    django.template.RequestContext(request, c))
  # By setting the content type ourselves, we gain control over the
  # character encoding and can properly set the content length.
  ec = content.encode("UTF-8")
  r = django.http.HttpResponse(ec, content_type="text/html; charset=UTF-8")
  r["Content-Length"] = len(ec)
  return r

def staticHtmlResponse (content):
  r = django.http.HttpResponse(content,
    content_type="text/html; charset=UTF-8")
  r["Content-Length"] = len(content)
  return r

def plainTextResponse (message):
  r = django.http.HttpResponse(message, content_type="text/plain")
  r["Content-Length"] = len(message)
  return r

# Our development version of Python (2.5) doesn't have the standard
# JSON module (introduced in 2.6), so we provide our own encoder here.

_jsonRe = re.compile("[\\x00-\\x1F\"\\\\\\xFF]")
def json (o):
  if type(o) is dict:
    assert all(type(k) is str for k in o), "unexpected object type"
    return "{" + ", ".join(json(k) + ": " + json(v) for k, v in o.items()) +\
      "}"
  elif type(o) is list:
    return "[" + ", ".join(json(v) for v in o) + "]"
  elif type(o) is str or type(o) is unicode:
    return "\"" + _jsonRe.sub(lambda c: "\\u%04X" % ord(c.group(0)), o) + "\""
  elif type(o) is bool:
    return "true" if o else "false"
  else:
    assert False, "unexpected object type"

def jsonResponse (data):
  # Per RFC 4627, the default encoding is understood to be UTF-8.
  ec = json(data).encode("UTF-8")
  r = django.http.HttpResponse(ec, content_type="application/json")
  r["Content-Length"] = len(ec)
  return r

_redirect = django.http.HttpResponseRedirect

def _error (code):
  content = templates[str(code)].render(django.template.Context())
  return django.http.HttpResponse(content, status=code)

def badRequest ():
  return _error(400)

def unauthorized ():
  return _error(401)

def methodNotAllowed ():
  return _error(405)

def formatError (message):
  for p in ["error: bad request - ", "error: "]:
    if message.startswith(p) and len(message) > len(p):
      return message[len(p)].upper() + message[len(p)+1:] + "."
  return message

def getPrefixes (user, group):
  try:
    return [{ "namespace": prefixes.get(p, "?"), "prefix": p }\
      for p in policy.getPrefixes(user, group)]
  except Exception, e:
    log.otherError("ui._getPrefixes", e)
    return "error: internal server error"