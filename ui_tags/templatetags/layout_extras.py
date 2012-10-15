from django import template
from django.conf import settings
from django.utils.html import escape
from decorators import basictag
from django.core.urlresolvers import reverse
import urllib
#import pdb
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
  if key_name in request.REQUEST:
    return escape(request.REQUEST[key_name])
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
def help_icon(id_of_help):
  return '&nbsp;&nbsp;&nbsp;&nbsp;<a href="#' + id_of_help + '" name="help_link">' + \
    '<img src="/ezid/static/images/help_icon.gif" alt="Click for additional help"' + \
    ' title="Click for additional help"/></a>'


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
  if key_name in request.REQUEST and request.REQUEST[key_name] != '':
    return escape(request.REQUEST[key_name])
  else:
    return escape(default)

@register.tag
@basictag(takes_context=True)
def selected_radio(context, request_item, loop_index, item_value):
  """returns checked="checked" if this should be the currently selected
  radio button based on matching request data or 1st item and nothing selected"""
  request = context['request']
  if request_item in request.REQUEST and request.REQUEST[request_item] == item_value:
    return 'checked="checked"'
  elif request_item not in request.REQUEST and loop_index == 1:
    return 'checked="checked"'
  else:
    return ''

@register.simple_tag
def shoulder_display(prefix_dict, testPrefixes):
  for pre in testPrefixes:
    if prefix_dict['prefix'].startswith(pre['prefix']):
      return escape(prefix_dict['namespace']) + " (<span class='fakeid'>" + escape(prefix_dict['prefix']) + "</span>)"
  return escape(prefix_dict['namespace'] + " (" + prefix_dict['prefix'] + ")")

@register.simple_tag
def search_display(dictionary, field):
  if field in ['createTime', 'updateTime']:
    return escape(datetime.datetime.fromtimestamp(dictionary[field]))
  else:
    return dictionary[field]

# This function should and will be moved to a better location.  -GJ
def _urlForm (id):
  if id.startswith("doi:"):
    return "http://dx.doi.org/" + urllib.quote(id[4:], ":/")
  elif id.startswith("ark:/") or id.startswith("urn:uuid:"):
    return "http://n2t.net/" + urllib.quote(id, ":/")
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

  
#This captures the block around with rounded corners go, can't believe what a PITA this is in django
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
        <img src="/ezid/static/images/corners/tl.gif" width="6" height="6" class="roundtl" />
        <img src="/ezid/static/images/corners/tr.gif" width="6" height="6" class="roundtr" />
        <img src="/ezid/static/images/corners/bl.gif" width="6" height="6" class="roundbl" />
        <img src="/ezid/static/images/corners/br.gif" width="6" height="6" class="roundbr" />
        <div class="roundboxpad">
    %(content)s
    </div></div>""" % {'content':content,}
    

  