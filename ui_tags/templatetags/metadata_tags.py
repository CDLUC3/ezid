from django import template
import re
from django.conf import settings
from django.utils.html import escape
import time
from decorators import basictag
import layout_extras


register = template.Library()

@register.simple_tag
def display_value(id_dictionary, element):
  """Takes the id metadata dictionary and element object."""
  if element.name in id_dictionary:
    return display_formatted(id_dictionary, element)
  else:
    if element.name == '_coowners':
      return 'none'
    return '[No value]'

def display_formatted(id_dictionary, element):
  """formats the element object according to its display style"""
  if element.displayType == 'datetime':
    t = time.localtime(float(id_dictionary[element.name]))
    return time.strftime(settings.TIME_FORMAT_UI_METADATA, t)
  elif element.displayType == 'url':
    return "<a href='" + id_dictionary[element.name] + "'>" + escape(id_dictionary[element.name]) + "</a>"
  elif element.displayType == 'boolean':
    if id_dictionary[element.name].upper() == 'TRUE' or id_dictionary[element.name].upper() == "YES":
      return 'Yes'
    else:
      return 'No'
  elif element.displayType == 'is_public':
    if id_dictionary[element.name] == 'public':
      return 'Yes'
    else:
      return 'No'
  else:
    return escape(id_dictionary[element.name])
  
@register.tag
@basictag(takes_context=True)
def display_form_element(context, element, id_object=None):
  """Displays a form element as indicated in the profile.
  Automatically pulls re-POSTed values and object (optional)"""
  if element.displayType.startswith('text'):
    return display_text_box(context, element, id_object)
  elif element.displayType.startswith('select:'):
    opts = eval(element.displayType[len('select:'):])
    return display_select(context, element, opts, id_object)
  return ''

def display_text_box(context, element, id_object):
  """displays a text box based on the element"""
  return "<input type=\"text\" class=\"%s std_form_width\" name=\"%s\" id=\"%s\" size=\"35\" value=\"%s\" />" \
    % tuple([escape(x) for x in(layout_extras.tooltip_class(element.name),
       element.name,
       element.name,
       _form_value(context, element.name, id_object),
      )])

def display_select(context, element, options, id_object):
  """displays a select list based on the element"""
  sel_part = "<select class=\"%s\" name=\"%s\" id=\"%s\">" % ( layout_extras.tooltip_class(element.name), element.name, element.name, )
  selected = _form_value(context, element.name, id_object)
  return sel_part + ''.join(
      [("<option value=\"" + escape(x[0]) + "\" " + ("selected=\"selected\"" if x[0] == selected  else '') +">" + \
        escape(x[1]) + "</option>") for x in options]) +\
      "</select>"

def _request_value(context, key_name):
  """gets the value of context[key_name]"""
  request = context['request']
  if key_name in request.REQUEST:
    return request.REQUEST[key_name]
  else:
    return ''
  
def _form_value(context, key_name, id_object):
  """Gets a value in this priority 1) request, 2) id_object, 3) default of ''"""
  val = ''
  if id_object != None and key_name in id_object:
    val = id_object[key_name]
  request = context['request']
  if key_name in request.REQUEST:
    val = request.REQUEST[key_name]
  return val
