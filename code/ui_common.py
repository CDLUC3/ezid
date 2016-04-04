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
import string
from random import choice

import config
import datacite
import ezid
import ezidadmin
import ezidapp.models.server_variables
import idmap
import log
import newsfeed 
import policy
import ezidapp.models.shoulder
import useradmin
import userauth
import django.contrib.messages
import urlparse
from django.utils.translation import ugettext as _

ezidUrl = None
templates = None # { name: (template, path), ... }
alertMessage = None
testPrefixes = None
defaultDoiProfile = None
defaultArkProfile = None
defaultUrnUuidProfile = None
adminUsername = None
google_analytics_id = None
new_account_email = None
reload_templates = None
newsfeed_url = None

manual_profiles = {'datacite_xml': 'DataCite'}

def _loadConfig():
  #these aren't really globals for the whole app, but globals for ui_common
  #outside of this module, use ui_common.varname
  global ezidUrl, templates, alertMessage, testPrefixes
  global defaultDoiProfile, defaultArkProfile, defaultUrnUuidProfile
  global adminUsername, google_analytics_id
  global new_account_email, reload_templates, newsfeed_url
  ezidUrl = config.get("DEFAULT.ezid_base_url")
  templates = {}
  _load_templates([d for t in django.conf.settings.TEMPLATES\
    for d in t["DIRS"]])
  alertMessage = ezidapp.models.server_variables.getAlertMessage()
  reload_templates = hasattr(django.conf.settings, 'RELOAD_TEMPLATES')
  if reload_templates:
    reload_templates = django.conf.settings.RELOAD_TEMPLATES
  testPrefixes = []
  p = ezidapp.models.shoulder.getArkTestShoulder()
  if p != None: testPrefixes.append({ "namespace": p.name, "prefix": p.prefix })
  p = ezidapp.models.shoulder.getDoiTestShoulder()
  if p != None: testPrefixes.append({ "namespace": p.name, "prefix": p.prefix })
  defaultDoiProfile = config.get("DEFAULT.default_doi_profile")
  defaultArkProfile = config.get("DEFAULT.default_ark_profile")
  defaultUrnUuidProfile = config.get("DEFAULT.default_urn_uuid_profile")
  adminUsername = config.get("ldap.admin_username")
  google_analytics_id = config.get("DEFAULT.google_analytics_id")
  new_account_email = config.get("email.new_account_email")
  newsfeed_url = config.get("newsfeed.url")
  
#loads the templates directory recursively (dir_list is a list)
def _load_templates(dir_list):
  global templates
  my_dir = apply(os.path.join, dir_list)
  for f in os.listdir(my_dir):
    if os.path.isdir(os.path.join(my_dir,f)):
      _load_templates(dir_list + [f])
    elif os.path.isfile(os.path.join(my_dir,f)) and f.endswith(".html"):
      local_path = apply(os.path.join, dir_list[1:] + [f])
      templates[local_path[:-5]] =\
        (django.template.loader.get_template(local_path), local_path)

_loadConfig()
config.registerReloadListener(_loadConfig)
  
def render(request, template, context={}):
  global alertMessage, google_analytics_id, reload_templates
  c = { "session": request.session, "alertMessage": alertMessage, "feed_cache": newsfeed.getLatestItem(), "rss_feed": newsfeed_url, "google_analytics_id": google_analytics_id }
  c.update(context)
  #this is to keep from having to restart the server every 3 seconds
  #to see template changes in development, only reloads if set for optimal performance
  if reload_templates:
    templ = django.template.loader.get_template(templates[template][1])
  else:
    templ = templates[template][0]
  content = templ.render(
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

def staticTextResponse (content):
  r = django.http.HttpResponse(content,
    content_type="text/plain; charset=UTF-8")
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

redirect = django.http.HttpResponseRedirect

def error (request, code, content_custom=None):
  t = django.template.RequestContext(request, {'menu_item' : 'ui_home.null', 
    'content_custom' : content_custom})
  content = templates[str(code)][0].render(t)
  return django.http.HttpResponse(content, status=code)

def badRequest (request):
  return error(request, 400)

def unauthorized (request):
  return error(request, 401)

def methodNotAllowed (request):
  return error(request, 405)

def formatError (message):
  for p in [_("error: bad request - "), _("error: ")]:
    if message.startswith(p) and len(message) > len(p):
      return message[len(p)].upper() + message[len(p)+1:] + "."
  return message

def getPrefixes (user, group):
  try:
    return [{ "namespace": s.name, "prefix": s.prefix }\
      for s in policy.getShoulders(user, group)]
  except Exception, e:
    log.otherError("ui_common.getPrefixes", e)
    return _("error: internal server error")
  
def is_logged_in(request):
  if "auth" not in request.session:
    django.contrib.messages.error(request, _("You must be logged in to view this page"))
    request.session['redirect_to'] = request.get_full_path()
    return False
  return True

def authorizeCreate(request, prefix):
  """a simple function to decide if a user (gotten from request.session)
  is allowed to create with the prefix"""
  return policy.authorizeCreate(user_or_anon_tup(request), group_or_anon_tup(request),
        prefix)

def authorizeUpdate(request, metadata_tup):
  """a simple function to decide if identifier can updated/edited based in ui values.
  It takes the request object (for session) and presumed object metadata tuple. It wraps
  the much more complicated policy function calls so they're simple to use in multiple places
  without repeating a lot of code."""
  if not (type(metadata_tup) is tuple):
    return False
  s, m = metadata_tup
  if not s.startswith("success:"):
    return False
  the_id = s.split()[1]
  #just gets the updating items found on the edit screen
  to_update = [x for x in m.keys() if not (x.startswith('_') and not x in ['_status','_target', '_profile']) ]
  return policy.authorizeUpdate(user_or_anon_tup(request), group_or_anon_tup(request),
        the_id, get_user_tup(m['_owner']), get_group_tup(m['_ownergroup']),
        get_coowners_tup(m), to_update)

# simple function to decide if identifier can be deleted based on ui context
def authorizeDelete(request, metadata_tup):
  """a simple function to decide if identifier can be deleted based in ui values.
  It takes the request object (for session) and presumed object metadata tuple. It wraps
  the much more complicated policy function calls so they're simple to use in multiple places
  without repeating a lot of code."""
  if not (type(metadata_tup) is tuple):
    return False
  s, m = metadata_tup
  if not s.startswith("success:"):
    return False
  the_id = s.split()[1]
  return policy.authorizeDelete(user_or_anon_tup(request), group_or_anon_tup(request),
        the_id, get_user_tup(m['_owner']), get_group_tup(m['_ownergroup']),
        get_coowners_tup(m))

def assembleUpdateDictionary (request, profile, additionalElements={}):
  d = { "_profile": profile.name }
  for e in profile.elements:
    if e.name in request.POST: d[e.name] = request.POST[e.name]
  d.update(additionalElements)
  return d

def user_or_anon_tup(request):
  """Gets user tuple from request.session, otherwise returns anonymous tuple"""
  if 'auth' in request.session:
    return request.session["auth"].user
  else:
    return ("anonymous", "anonymous")
    
def group_or_anon_tup(request):
  """Gets group tuple from request.session, otherwise returns anonymous tuple"""
  if 'auth' in request.session:
    return request.session["auth"].group
  else:
    return ("anonymous", "anonymous")
  
def get_user_tup(user_id):
  """Gets user tuple from user_id"""
  return (user_id, idmap.getUserId(user_id) )

def get_group_tup(group_id):
  """Gets group tuple from group_id"""
  return (group_id, idmap.getGroupId(group_id))

def get_coowners_tup(id_meta):
  if "_coowners" not in id_meta:
    return []
  else:
    return [get_user_tup(co.strip())\
      for co in id_meta["_coowners"].split(";") if len(co.strip()) > 0]
    
def extract(d, keys):
  """Gets subset of dictionary based on keys in an array"""
  return dict((k, d[k]) for k in keys if k in d)

def random_password(size = 8):
  return ''.join([choice(string.letters + string.digits) for i in range(size)])

def user_login_required(f):
  """defining a decorator to require a user to be logged in"""
  def wrap(request, *args, **kwargs):
    if 'auth' not in request.session.keys():
      request.session['redirect_to'] = request.get_full_path()
      django.contrib.messages.error(request, _("You must be logged in to view this page."))
      return django.http.HttpResponseRedirect("/login")
    return f(request, *args, **kwargs)
  wrap.__doc__=f.__doc__
  wrap.__name__=f.__name__
  return wrap

def admin_login_required(f):
  """defining a decorator to require an admin to be logged in"""
  def wrap(request, *args, **kwargs):
    if "auth" not in request.session or request.session["auth"].user[0] != adminUsername:
      request.session['redirect_to'] = request.get_full_path()
      django.contrib.messages.error(request, _("You must be logged in as an administrator to view this page."))
      return django.http.HttpResponseRedirect("/login")
    return f(request, *args, **kwargs)
  wrap.__doc__=f.__doc__
  wrap.__name__=f.__name__
  return wrap

def identifier_has_block_data (identifier):
  """
  Returns true if the identifier has block metadata, which affects
  both the display and the editability of the metadata in the UI.
  """
  return (identifier["_profile"] == "erc" and "erc" in identifier) or\
    (identifier["_profile"] == "datacite" and "datacite" in identifier)
