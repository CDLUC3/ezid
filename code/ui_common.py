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
import idmap
import log
import policy
import useradmin
import userauth
import django.contrib.messages
import urlparse

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
google_analytics_id = None
contact_form_email = None
new_customer_email = None
reload_templates = None
newsfeed_url = None

remainder_box_default = "Recommended: Leave blank"

def _loadConfig():
  #these aren't really globals for the whole app, but globals for ui_common
  #outside of this module, use ui_common.varname
  global ezidUrl, templates, alertMessage, prefixes, testPrefixes
  global defaultDoiProfile, defaultArkProfile, defaultUrnUuidProfile
  global adminUsername, shoulders, google_analytics_id, contact_form_email
  global new_customer_email, reload_templates, newsfeed_url
  ezidUrl = config.config("DEFAULT.ezid_base_url")
  templates = {}
  _load_templates([ django.conf.settings.TEMPLATE_DIRS[0] ])
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
  reload_templates = hasattr(django.conf.settings, 'RELOAD_TEMPLATES')
  if reload_templates:
    reload_templates = django.conf.settings.RELOAD_TEMPLATES
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
  google_analytics_id = config.config("DEFAULT.google_analytics_id")
  contact_form_email = config.config("email.contact_form_email")
  new_customer_email = config.config("DEFAULT.new_customer_email")
  shoulders = [{ "label": k, "name": config.config("prefix_%s.name" % k),
    "prefix": config.config("prefix_%s.prefix" % k) }\
    for k in config.config("prefixes.keys").split(",")\
    if not k.startswith("TEST")]
  newsfeed_url = config.config("newsfeed.url")
  
#loads the templates directory recursively (dir_list is a list)
#beginning with first list item django.conf.settings.TEMPLATE_DIRS[0]
def _load_templates(dir_list):
  global templates
  my_dir = apply(os.path.join, dir_list)
  for f in os.listdir(my_dir):
    if os.path.isdir(os.path.join(my_dir,f)):
      _load_templates(dir_list + [f])
    elif os.path.isfile(os.path.join(my_dir,f)) and f.endswith(".html"):
      local_path = apply(os.path.join, dir_list[1:] + [f])
      templates[local_path[:-5]] = django.template.loader.get_template(local_path)

_loadConfig()
config.addLoader(_loadConfig)
  
def render(request, template, context={}):
  global alertMessage, google_analytics_id, reload_templates
  c = { "session": request.session, "alertMessage": alertMessage, "google_analytics_id": google_analytics_id }
  c.update(context)
  #this is to keep from having to restart the server every 3 seconds
  #to see template changes in development, only reloads if set for optimal performance
  if reload_templates:
    templ = django.template.loader.get_template(os.path.join(\
          django.conf.settings.TEMPLATE_DIRS[0], template) + '.html')
  else:
    templ = templates[template]
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

def error (code):
  content = templates[str(code)].render(django.template.Context())
  return django.http.HttpResponse(content, status=code)

def badRequest ():
  return error(400)

def unauthorized ():
  return error(401)

def methodNotAllowed ():
  return error(405)

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
  
def is_logged_in(request):
  if "auth" not in request.session:
    django.contrib.messages.error(request, "You must be logged in to view this page")
    request.session['redirect_to'] = request.get_full_path()
    return False
  return True

def view_authorized_for_identifier(request, id_meta):
  """Checks that the user is authorized to view identifier"""
  if "_ezid_role" in id_meta and ("auth" not in request.session or\
    request.session["auth"].user[0] != adminUsername):
    django.contrib.messages.error(request, "Unauthorized.")
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
  return policy.authorizeUpdate(user_or_anon_tup(request), group_or_anon_tup(request),
        the_id, get_user_tup(m['_owner']), get_group_tup(m['_ownergroup']),
        get_coowners_tup(m), m)

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

_dataciteResourceTypes = ["Collection", "Dataset", "Event", "Film", "Image",
  "InteractiveResource", "Model", "PhysicalObject", "Service", "Software",
  "Sound", "Text"]

def validate_simple_metadata_form(request, profile):
  """validates a simple id metadata form, profile is more or less irrelevant for now,
  but may be useful later"""
  is_valid = True
  if "_target" not in request.POST:
    django.contrib.messages.error(request, "You must enter a location (URL) for your identifier")
    is_valid = False
  if not(url_is_valid(request.POST['_target'])):
    django.contrib.messages.error(request, "Please enter a a valid location (URL)")
    is_valid = False
  if "datacite.resourcetype" in request.POST:
    rt = request.POST["datacite.resourcetype"].strip()
    if rt != "" and rt.split("/", 1)[0] not in _dataciteResourceTypes:
      django.contrib.messages.error(request, "Invalid general resource type")
      is_valid = False
  return is_valid

def validate_advanced_metadata_form(request, profile):
  """validates an advanced metadata form, profile is more or less irrelevant for now,
  but may be useful later"""
  is_valid = True
  if "_target" not in request.POST:
    django.contrib.messages.error(request, "You must enter a location (URL) for your identifier")
    is_valid = False  
  if not(url_is_valid(request.POST['_target'])):
    django.contrib.messages.error(request, "Please enter a valid location (URL)")
    is_valid = False
  if request.POST['remainder'] != '' and request.POST['remainder'] != remainder_box_default and \
      (' ' in request.POST['remainder']):
    django.contrib.messages.error(request, "The remainder you entered is not valid.")
    is_valid = False       
  if "datacite.resourcetype" in request.POST:
    rt = request.POST["datacite.resourcetype"].strip()
    if rt != "" and rt.split("/", 1)[0] not in _dataciteResourceTypes:
      django.contrib.messages.error(request, "Invalid general resource type")
      is_valid = False
  return is_valid

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

def fix_target(target):
  """Fixes a target URL if it does not include the protocol at first so it defaults to http://"""
  url = urlparse.urlparse(target)
  if target != '' and not(url.scheme and url.netloc):
    return 'http://' + target
  else:
    return target
  
def url_is_valid(target):
  """ checks whether a url is likely valid, with our without scheme and allows for blank urls """
  if target == '':
    return True
  url = urlparse.urlparse(target)
  if url.scheme == '':
    url = urlparse.urlparse('http://' + target)
  netloc_regex = re.compile('^[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,4}(\:\d+)?$')
  if not(url.scheme and url.netloc and netloc_regex.match(url.netloc)):
    return False
  return True
  
def random_password(size = 8):
  return ''.join([choice(string.letters + string.digits) for i in range(size)])

def user_login_required(f):
  """defining a decorator to require a user to be logged in"""
  def wrap(request, *args, **kwargs):
    if 'auth' not in request.session.keys():
      request.session['redirect_to'] = request.get_full_path()
      django.contrib.messages.error(request, 'You must be logged in to view this page.')
      return django.http.HttpResponseRedirect("/ezid/login")
    return f(request, *args, **kwargs)
  wrap.__doc__=f.__doc__
  wrap.__name__=f.__name__
  return wrap

def admin_login_required(f):
  """defining a decorator to require an admin to be logged in"""
  def wrap(request, *args, **kwargs):
    if "auth" not in request.session or request.session["auth"].user[0] != adminUsername:
      request.session['redirect_to'] = request.get_full_path()
      django.contrib.messages.error(request, 'You must be logged in as an administrator to view this page.')
      return django.http.HttpResponseRedirect("/ezid/login")
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
