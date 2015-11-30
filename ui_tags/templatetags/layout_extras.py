from django import template
from django.conf import settings
from django.utils.html import escape
from django.utils.translation import ugettext as _
from decorators import basictag
from django.core.urlresolvers import reverse
from operator import itemgetter
import config 
import django.template
import urllib
import re
from lxml import etree, objectify
#import datetime

register = template.Library()

# settings value
@register.simple_tag
def settings_value(name):
  """ Gets a value from the settings configuration"""
  try:
    return settings.__getattr__(name)
  except AttributeError:
    return ""
  
@register.simple_tag
def content_heading(heading):
  """Outputs primary heading at top of page"""
  return '<div class="header"><div class="container"><div class="row"><h1>' + \
         unicode(heading) + '</h1></div></div></div>'

@register.simple_tag
def choices(name, value, choice_string):
  """Creates radio buttons (for simple admin email form) based on string choices separated by a pipe"""
  choices = choice_string.split("|")
  return "  ".join(
          ['<input type="radio" name="' + name + '" value="' + escape(x) + '"' +
            (' checked="checked"' if value == x else '') + '>' + escape(x) + '</input>'
           for x in choices])

@register.tag
@basictag(takes_context=True) 
def request_value(context, key_name):
  """Outputs the value of context[key_name], required because
  normal django templating will not retrieve any variables starting with an underscore
  which all of the internal profile variables have"""
  request = context['request']
  if request.method == "GET":
    REQUEST = request.GET
  else:
    REQUEST = request.POST
  if key_name in REQUEST:
    return escape(REQUEST[key_name])
  else:
    return ''
  
@register.tag
@basictag(takes_context=True) 
def set_dict_value(context, dt, key_name):
  """Sets value in the context object equal to the dictionary dt[key_name]"""
  context['value'] = dt[key_name]
  return ''

@register.simple_tag
def get_dict_value(dt, key_name):
  """For getting dictionary values which Django templating can't handle,
  such as those starting with underscore or with a dot in them"""
  if key_name in dt:
    return escape(dt[key_name])
  else:
    return ''
  
@register.simple_tag
def tooltip_class(profile_element_string):
  return escape('element_' + profile_element_string.replace('.',''))

@register.simple_tag
def identifier_display(id_text, testPrefixes):
  for pre in testPrefixes:
    if id_text.startswith(pre['prefix']):
      return "<span class='fakeid'>" + escape(id_text) + "</span>"
  return escape(id_text)

@register.simple_tag
def active_id_display(id_text, testPrefixes):
  #remove yellow highlighting for demo_id's URL
  #for pre in testPrefixes:
  #  if id_text.startswith(pre['prefix']):
  #    return "<span class='fakeid'>" + '<a href="' + _urlForm(id_text) + '">' + _urlForm(id_text) + '</a></span>'
  return '<a href="' + _urlForm(id_text) + '">' + _urlForm(id_text) + '</a>'

@register.simple_tag
def help_icon(id_of_help):
  return '<a id="' + id_of_help + '" role="button" data-toggle="popover" data-trigger="click">' + \
    '<img src="/static/images/iconHelp.svg" alt="Click for additional help"' + \
    ' class="icon-help" title="Click for additional help"/></a>'

@register.simple_tag
def datacite_field_help_icon(id_of_help):
  temp_id = id_of_help.replace(".", "_") + '_help'
  return '<a id="' + temp_id + '" role="button" data-toggle="popover" data-trigger="click">' + \
    '<img src="/static/images/iconHelp.svg" alt="Click for additional help"' + \
    ' class="icon-help" title="Click for additional help"/></a>'  

@register.tag
@basictag(takes_context=True)
def url_force_https(context, url_path):
  """Force link to be prefixed wth https"""
  request = context['request']
  if django.conf.settings.SSL and ('HTTP_HOST' in request.META):
    url_path_no_lead_slash = url_path[1:] if re.match('^\/.*', url_path) else url_path
    return "%s//%s/%s" % ('https:', request.META.get("HTTP_HOST"), url_path_no_lead_slash)
  else:
    return url_path

@register.tag
@basictag(takes_context=True)
def host_based_include(context, template_path):
  """This includes a file from a different directory instead of the
  normal specified file based on the hostname.  This allows for some
  simple branding changes in the templates based host name differences"""
  request = context['request']
  host = request.META.get("HTTP_HOST", "default")
  if host not in django.conf.settings.LOCALIZATIONS: host = "default"
  template_path = template_path.replace("/_/",
    "/%s/" % django.conf.settings.LOCALIZATIONS[host][0])
  t = django.template.loader.get_template(template_path)
  return t.render(context)

#@register.simple_tag(takes_context=True)
@register.tag
@basictag(takes_context=True) 
def form_or_dict_value(context, dict, key_name):
  """Outputs the value of the dict[key_name] unless request.POST contains the data
  for the item which then overrides the dictionary's value.
  This both fixes problems with normal django templating which will not retrieve
  any keys starting with an underscore and it solves the problem of re-POSTed values
  which were getting clobbered by the stored values.  POSTed values should override
  so people do not lose their in-process edits.
  """
  request = context['request']
  if request.POST and key_name in request.POST:
    return escape(request.POST[key_name])
    #return escape(request['POST'][key_name])
  elif key_name in dict:
    return escape(dict[key_name])
  else:
    return ''
  
@register.tag
@basictag(takes_context=True) 
def form_or_default(context, key_name, default):
  """Outputs the value of the reposted value unless it doesn't exist then 
  outputs the default value passed in.
  """
  request = context['request']
  if request.method == "GET":
    REQUEST = request.GET
  else:
    REQUEST = request.POST
  if key_name in REQUEST and REQUEST[key_name] != '':
    return escape(REQUEST[key_name])
  else:
    return escape(default)

@register.tag
@basictag(takes_context=True)
def selected_radio(context, request_item, loop_index, item_value):
  """returns checked="checked" if this should be the currently selected
  radio button based on matching request data or 1st item and nothing selected"""
  request = context['request']
  if request.method == "GET":
    REQUEST = request.GET
  else:
    REQUEST = request.POST
  if request_item in REQUEST and REQUEST[request_item] == item_value:
    return 'checked="checked"'
  elif request_item not in REQUEST and loop_index == 1:
    return 'checked="checked"'
  else:
    return ''

@register.simple_tag
def shoulder_display(prefix_dict, id_type_only="False", testPrefixes=[], sans_namespace="False"):
  """Three types of display:
  FULL --------------->  Caltech Biology ARK (ark:/77912/w7))
  SANS NAMESPACE ----->    ARK (ark:/99999/...))       <----------   used for demo page
  ID TYPE ONLY ------->    ARK                         <----------   used for home page"""
  if id_type_only == "False":
    display_prefix = ""
    for pre in testPrefixes:
      if prefix_dict['prefix'].startswith(pre['prefix']):
        display_prefix = " (" + escape(prefix_dict['prefix']) + "/... )"
    if display_prefix == '':
      display_prefix = " (" + prefix_dict['prefix'] + ")"
    if sans_namespace == "True":
      return escape(_get_id_type(prefix_dict['prefix'])) + display_prefix
    else:
      type = _get_id_type(prefix_dict['prefix'])
      return escape(prefix_dict['namespace'] + ' ' + type) + display_prefix 
  else:
    return escape(_get_id_type(prefix_dict['prefix']))

def _get_id_type (prefix):
  t = prefix.split(":")[0].upper()
  return t

@register.simple_tag
def search_display(dictionary, field):
  if field in ['createTime', 'updateTime']:
    return escape(datetime.datetime.fromtimestamp(dictionary[field]))
  else:
    return dictionary[field]
  
@register.simple_tag
def unavailable_codes(for_field):
  items = ( ("unac", "temporarily inaccessible"),
            ("unal", "unallowed, suppressed intentionally"),
            ("unap", "not applicable, makes no sense"),
            ("unas", "value unassigned (e.g., Untitled)"),
            ("unav", "value unavailable, possibly unknown"),
            ("unkn", "known to be unknown (e.g., Anonymous, Inconnue)"),
            ("none", "never had a value, never will"),
            ("null", "explicitly and meaningfully empty"),
            ("tba", "to be assigned or announced later"),
            ("etal", "too numerous to list (et alia)"),
            ("at", "the real value is at the given URL or identifier") )
  return "<ul>" + "\n".join(
          ["<li><a href=\"#"+ escape(x[0]) + "_" + for_field + "\" name=\"code_insert_link\">" + \
           escape("(:" + x[0] + ")" ) + "</a> " + escape(x[1]) + "</li>" for \
           x in items]
          ) + "</ul>"
    #<li><a href="#unas_datacite.creator" name="code_insert_link">(:unac)</a> temporarily inacessible</li>

# This function should and will be moved to a better location.  -GJ
def _urlForm (id):
  if id.startswith("doi:"):
    return "%s/%s" % (config.get("resolver.doi"), urllib.quote(id[4:], ":/"))
  elif id.startswith("ark:/") or id.startswith("urn:uuid:"):
    return "%s/%s" % (config.get("resolver.ark"), urllib.quote(id, ":/"))
  else:
    return "[None]"

@register.tag
@basictag(takes_context=True)
def full_url_to_id_details(context, id_text):
  """return URL form of identifier"""
  return _urlForm(id_text)
  
@register.tag
@basictag(takes_context=True)
def full_url_to_id_details_urlencoded(context, id_text):
  """return URL form of identifier, URL-encoded"""
  return urllib.quote(_urlForm(id_text))

#check for more than one of the same identifer type
#NOT checking for duplicate shoulders, returns t/f
@register.filter(name='duplicate_id_types')
def duplicate_id_types(prefixes):
  kinds = {}
  for prefix in prefixes:
    t = re.search('^[A-Za-z]+:', prefix['prefix'])
    t = t.group(0)[:-1]
    if t in kinds:
      kinds[t] = kinds[t] + 1
    else:
      kinds[t] = 1
  for key, value in kinds.iteritems():
    if value > 1:
      return True
  return False

#returns list of unique ID types such as ARK/DOI/URN with the
#prefix information, ((prefix, prefix_obj), etc)
#should only be called where only one prefix per type
@register.filter(name='unique_id_types')
def unique_id_types(prefixes):
  kinds = {}
  for prefix in prefixes:
    t = re.search('^[A-Za-z]+:', prefix['prefix'])
    t = t.group(0)[:-1]
    kinds[t] = prefix
  i = [(x[0].upper(), x[1],) for x in kinds.items()]
  return sorted(i, key = itemgetter(0))
  
#This captures the block around which rounded corners go
@register.tag(name="rounded_borders")
def do_rounded_borders(parser, token):
  nodelist = parser.parse(('endrounded_borders'))
  parser.delete_first_token()
  return FormatRoundedBordersNode(nodelist)

class FormatRoundedBordersNode(template.Node):
  def __init__(self,nodelist):
    self.nodelist = nodelist

  def render(self, context):
    content = self.nodelist.render(context)
    return """<div class="roundbox">
        <img src="/static/images/corners/tl.gif" width="6" height="6" class="roundtl" />
        <img src="/static/images/corners/tr.gif" width="6" height="6" class="roundtr" />
        <img src="/static/images/corners/bl.gif" width="6" height="6" class="roundbl" />
        <img src="/static/images/corners/br.gif" width="6" height="6" class="roundbr" />
        <div class="roundboxpad">
    %(content)s
    </div></div>""" % {'content':content,}


''' -------------------------------------------------------------------
For editing (and creating) DataCite advanced DOI elements: If object representing
XML blob does not have element we're looking for, load an empty one
    -------------------------------------------------------------------'''    
@register.inclusion_tag('create/_datacite_altId.html')
def datacite_get_altIds(datacite_obj, datacite_obj_empty):
  if hasattr(datacite_obj, 'alternateIdentifiers') and\
      hasattr(datacite_obj.alternateIdentifiers, 'alternateIdentifier'):
      datacite_obj_alternateIdentifiers = datacite_obj.alternateIdentifiers
  else:
      datacite_obj_alternateIdentifiers = datacite_obj_empty.alternateIdentifiers
  num_altIds = len(datacite_obj_alternateIdentifiers.alternateIdentifier) 
  num_altIds = num_altIds if num_altIds > 1 else 1
  return {'datacite_obj_alternateIdentifiers': 
          datacite_obj_alternateIdentifiers, 'num_altIds': num_altIds}

@register.inclusion_tag('create/_datacite_contributor.html')
def datacite_get_contributors(datacite_obj, datacite_obj_empty):
  if hasattr(datacite_obj, 'contributors') and\
      hasattr(datacite_obj.contributors, 'contributor'):
      datacite_obj_contributors = datacite_obj.contributors
  else:
      datacite_obj_contributors = datacite_obj_empty.contributors
  num_contributors = len(datacite_obj_contributors.contributor) 
  num_contributors = num_contributors if num_contributors > 1 else 1
  return {'datacite_obj_contributors': datacite_obj_contributors, 
          'num_contributors': num_contributors}

@register.inclusion_tag('create/_datacite_creator.html')
def datacite_get_creators(datacite_obj, datacite_obj_empty):
  if hasattr(datacite_obj, 'creators'):
    datacite_obj_creators = datacite_obj.creators
  else:
    datacite_obj_creators = datacite_obj_empty.creators
  num_creators = len(datacite_obj_creators.creator) 
  num_creators = num_creators if num_creators > 1 else 1
  return {'datacite_obj_creators': datacite_obj_creators, 
          'num_creators': num_creators}

@register.inclusion_tag('create/_datacite_date.html')
def datacite_get_dates(datacite_obj, datacite_obj_empty):
  if hasattr(datacite_obj, 'dates') and hasattr(datacite_obj.dates, 'date'):
      datacite_obj_dates = datacite_obj.dates
  else:
      datacite_obj_dates = datacite_obj_empty.dates
  num_dates = len(datacite_obj_dates.date) 
  num_dates = num_dates if num_dates > 1 else 1
  return {'datacite_obj_dates': datacite_obj_dates, 'num_dates': num_dates}

@register.inclusion_tag('create/_datacite_description.html')
def datacite_get_descriptions(datacite_obj, datacite_obj_empty):
  if hasattr(datacite_obj, 'descriptions') and\
    hasattr(datacite_obj.descriptions, 'description'):
    datacite_obj_descriptions = datacite_obj.descriptions
  else:
    datacite_obj_descriptions = datacite_obj_empty.descriptions
  num_descriptions = len(datacite_obj_descriptions.description) 
  num_descriptions = num_descriptions if num_descriptions > 1 else 1
  return {'datacite_obj_descriptions': datacite_obj_descriptions, 
          'num_descriptions': num_descriptions}

@register.inclusion_tag('create/_datacite_format.html')
def datacite_get_formats(datacite_obj, datacite_obj_empty):
  if hasattr(datacite_obj, 'formats') and\
    hasattr(datacite_obj.formats, 'format'):
    datacite_obj_formats = datacite_obj.formats
  else:
    datacite_obj_formats = datacite_obj_empty.formats
  num_formats = len(datacite_obj_formats.format)
  num_formats = num_formats if num_formats > 1 else 1
  return {'datacite_obj_formats': datacite_obj_formats, 
          'num_formats': num_formats}

@register.inclusion_tag('create/_datacite_geoLoc.html')
def datacite_get_geoLoc(datacite_obj, datacite_obj_empty):
  if hasattr(datacite_obj, 'geoLocations') and\
    hasattr(datacite_obj.geoLocations, 'geoLocation'):
    datacite_obj_geoLocations = datacite_obj.geoLocations
  else:
    datacite_obj_geoLocations = datacite_obj_empty.geoLocations
  num_geoLocations = len(datacite_obj_geoLocations.geoLocation)
  num_geoLocations = num_geoLocations if num_geoLocations > 1 else 1
  return {'datacite_obj_geoLocations': datacite_obj_geoLocations,
          'num_geoLocations': num_geoLocations}

@register.inclusion_tag('create/_datacite_relId.html')
def datacite_get_relIds(datacite_obj, datacite_obj_empty):
  if hasattr(datacite_obj, 'relatedIdentifiers') and\
    hasattr(datacite_obj.relatedIdentifiers, 'relatedIdentifier'):
    datacite_obj_relatedIdentifiers = datacite_obj.relatedIdentifiers
  else:
    datacite_obj_relatedIdentifiers = datacite_obj_empty.relatedIdentifiers
  num_relIds = len(datacite_obj_relatedIdentifiers.relatedIdentifier)
  num_relIds = num_relIds if num_relIds > 1 else 1
  return {'datacite_obj_relatedIdentifiers': datacite_obj_relatedIdentifiers,
         'num_relIds': num_relIds}

@register.inclusion_tag('create/_datacite_rights.html')
def datacite_get_rights(datacite_obj, datacite_obj_empty):
  if hasattr(datacite_obj, 'rightsList') and\
    hasattr(datacite_obj.rightsList, 'rights'):
    datacite_obj_rightsList = datacite_obj.rightsList
  else:
    datacite_obj_rightsList = datacite_obj_empty.rightsList
  num_rights = len(datacite_obj_rightsList.rights)
  num_rights = num_rights if num_rights > 1 else 1
  return {'datacite_obj_rightsList': datacite_obj_rightsList, 
          'num_rights': num_rights}

@register.inclusion_tag('create/_datacite_size.html')
def datacite_get_sizes(datacite_obj, datacite_obj_empty):
  if hasattr(datacite_obj, 'sizes') and hasattr(datacite_obj.sizes, 'size'):
    datacite_obj_sizes = datacite_obj.sizes
  else:
    datacite_obj_sizes = datacite_obj_empty.sizes
  num_sizes = len(datacite_obj_sizes.size) 
  num_sizes = num_sizes if num_sizes > 1 else 1
  return {'datacite_obj_sizes': datacite_obj_sizes, 
          'num_sizes': num_sizes}

@register.inclusion_tag('create/_datacite_subject.html')
def datacite_get_subjects(datacite_obj, datacite_obj_empty):
  if hasattr(datacite_obj, 'subjects') and\
    hasattr(datacite_obj.subjects, 'subject'):
    datacite_obj_subjects = datacite_obj.subjects
  else:
    datacite_obj_subjects = datacite_obj_empty.subjects
  num_subjects = len(datacite_obj_subjects.subject) 
  num_subjects = num_subjects if num_subjects > 1 else 1
  return {'datacite_obj_subjects': datacite_obj_subjects, 
          'num_subjects': num_subjects}

@register.inclusion_tag('create/_datacite_title.html')
def datacite_get_titles(datacite_obj, datacite_obj_empty):
  if hasattr(datacite_obj, 'titles'):
    datacite_obj_titles = datacite_obj.titles
  else:
    datacite_obj_titles = datacite_obj_empty.titles
  num_titles = len(datacite_obj_titles.title) 
  num_titles = num_titles if num_titles > 1 else 1
  return {'datacite_obj_titles': datacite_obj_titles, 'num_titles': num_titles}
