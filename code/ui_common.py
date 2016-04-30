import django.conf
import django.contrib.messages
import django.http
import django.template
import django.template.loader
import django.utils.http
import os
import re
import string
from random import choice

import config
import ezidapp.models
import userauth
import urlparse

ezidUrl = None
templates = None # { name: (template, path), ... }
alertMessage = None
testPrefixes = None
google_analytics_id = None
reload_templates = None
newsfeed_url = None

remainder_box_default = "Recommended: Leave blank"
manual_profiles = {'datacite_xml': 'DataCite'}

def _loadConfig():
  #these aren't really globals for the whole app, but globals for ui_common
  #outside of this module, use ui_common.varname
  global ezidUrl, templates, alertMessage, testPrefixes
  global google_analytics_id
  global reload_templates, newsfeed_url
  ezidUrl = config.get("DEFAULT.ezid_base_url")
  templates = {}
  _load_templates([d for t in django.conf.settings.TEMPLATES\
    for d in t["DIRS"]])
  alertMessage = ezidapp.models.getAlertMessage()
  reload_templates = hasattr(django.conf.settings, 'RELOAD_TEMPLATES')
  if reload_templates:
    reload_templates = django.conf.settings.RELOAD_TEMPLATES
  testPrefixes = []
  p = ezidapp.models.getArkTestShoulder()
  testPrefixes.append({ "namespace": p.name, "prefix": p.prefix })
  p = ezidapp.models.getDoiTestShoulder()
  testPrefixes.append({ "namespace": p.name, "prefix": p.prefix })
  google_analytics_id = config.get("DEFAULT.google_analytics_id")
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
  c = { "session": request.session,
    "authenticatedUser": userauth.getUser(request),
    "alertMessage": alertMessage, "google_analytics_id": google_analytics_id }
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

def error (code):
  content = templates[str(code)][0].render(django.template.Context())
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

def assembleUpdateDictionary (request, profile, additionalElements={}):
  d = { "_profile": profile.name }
  for e in profile.elements:
    if e.name in request.POST: d[e.name] = request.POST[e.name]
  d.update(additionalElements)
  return d

_dataciteResourceTypes = ["Audiovisual", "Collection", "Dataset", "Event", "Image",
  "InteractiveResource", "Model", "PhysicalObject", "Service", "Software",
  "Sound", "Text", "Workflow", "Other"]

def validate_simple_metadata_form(request, profile):
  """validates a simple id metadata form, profile is more or less irrelevant for now,
  but may be useful later"""
  is_valid = True
  post = request.POST
  msgs = django.contrib.messages
  if "_target" not in post:
    msgs.error(request, "You must enter a location (URL) for your identifier")
    is_valid = False
  if not(url_is_valid(post['_target'])):
    msgs.error(request, "Please enter a a valid location (URL)")
    is_valid = False
  if "datacite.resourcetype" in post:
    rt = post["datacite.resourcetype"].strip()
    if rt != "" and rt.split("/", 1)[0] not in _dataciteResourceTypes:
      msgs.error(request, "Invalid general resource type")
      is_valid = False
  if profile.name == 'datacite' and _validate_datacite_metadata_form(request, profile) == False:
    is_valid = False
  return is_valid

def validate_advanced_top(request):
  """validates advanced form top and returns list of error messages if any"""
  err_msgs = []
  post = request.POST
  if "_target" not in post:
    err_msgs.append("You must enter a location (URL) for your identifier") 
  if not(url_is_valid(post['_target'])):
    err_msgs.append("Please enter a valid location (URL)")
  if post['action'] == 'create' and \
      post['remainder'] != remainder_box_default and (' ' in post['remainder']):
    err_msgs.append("The remainder you entered is not valid.")     
  if "datacite.resourcetype" in post:
    rt = post["datacite.resourcetype"].strip()
    if rt != "" and rt.split("/", 1)[0] not in _dataciteResourceTypes:
      err_msgs.append("Invalid general resource type")
  return err_msgs
  
def validate_advanced_metadata_form(request, profile):
  """validates an advanced metadata form, profile is more or less irrelevant for now,
  but may be useful later
  Advanced Datacite DOI XML Blobs validation is done in ui_create.ajax_advanced"""
  err_msgs = validate_advanced_top(request)
  if len(err_msgs) > 0: #add any error messages to the request from top part
    is_valid = False
    for em in err_msgs:
      django.contrib.messages.error(request, em)
  else:
    is_valid = True
  if profile.name == 'datacite' and _validate_datacite_metadata_form(request, profile) == False:
    is_valid = False
  return is_valid

def _validate_datacite_metadata_form(request, profile):
  post = request.POST
  msgs = django.contrib.messages
  is_valid = True
  if profile.name != 'datacite' or ('publish' in post and post['publish'] == 'False') or\
    ('_status' in post and post['_status'] == 'reserved'):
    return True
  if not set(['datacite.creator', 'datacite.title', 'datacite.publisher', \
      'datacite.publicationyear', 'datacite.resourcetype']).issubset(post):
    msgs.error(request, "Some required form elements are missing")
    return False
  for x in ['datacite.creator', 'datacite.title', 'datacite.publisher']:
    if post[x].strip() == '':
      msgs.error(request, 'You must fill in a value for ' + x.split('.')[1] + ' or use one of the codes shown in the help.')
      is_valid = False
  codes = ['(:unac)', '(:unal)', '(:unap)', '(:unas)', '(:unav)', \
           '(:unkn)', '(:none)', '(:null)', '(:tba)', '(:etal)', \
           '(:at)']
  if not( post['datacite.publicationyear'] in codes or \
          re.search('^\d{4}$', post['datacite.publicationyear']) ):
    msgs.error(request, 'You must fill in a 4-digit publication year or use one of the codes shown in the help.')
    is_valid = False
    
  return is_valid

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
  netloc_regex = re.compile('^[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,30}(\:\d+)?$')
  if not(url.scheme and url.netloc and netloc_regex.match(url.netloc)):
    return False
  return True
  
def random_password(size = 8):
  return ''.join([choice(string.letters + string.digits) for i in range(size)])

def user_login_required(f):
  """defining a decorator to require a user to be logged in"""
  def wrap(request, *args, **kwargs):
    if userauth.getUser(request) == None:
      django.contrib.messages.error(request, 'You must be logged in to view this page.')
      return django.http.HttpResponseRedirect("/login?next=" +\
        django.utils.http.urlquote(request.get_full_path()))
    return f(request, *args, **kwargs)
  wrap.__doc__=f.__doc__
  wrap.__name__=f.__name__
  return wrap

def admin_login_required(f):
  """defining a decorator to require an admin to be logged in"""
  def wrap(request, *args, **kwargs):
    if not userauth.getUser(request, returnAnonymous=True).isSuperuser:
      django.contrib.messages.error(request, 'You must be logged in as an administrator to view this page.')
      return django.http.HttpResponseRedirect("/login?next=" +\
        django.utils.http.urlquote(request.get_full_path()))
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
