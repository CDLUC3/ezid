from django import template
import re
from django.utils.html import escape
import time


register = template.Library()

@register.simple_tag
def display_value(id_dictionary, element):
  """Takes the id metadata dictionary and element."""
  if element.name in id_dictionary:
    return display_formatted(id_dictionary, element)
  else:
    return '[No value]'

def display_formatted(id_dictionary, element):
  """formats the element according to its display style"""
  if element.displayType == 'datetime':
    t = time.localtime(float(id_dictionary[element.name]))
    return time.strftime("%m/%d/%Y %I:%M %p", t)
  elif element.displayType == 'url':
    return "<a href='" + id_dictionary[element.name] + "'>" + escape(id_dictionary[element.name]) + "</a>"
  elif element.displayType == 'boolean':
    if id_dictionary[element.name].upper() == 'TRUE':
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