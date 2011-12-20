from django import template
import re
from django.utils.html import escape


register = template.Library()

@register.simple_tag
def display_value(id_dictionary, element):
  """Takes the id metadata dictionary and element."""
  if element.name in id_dictionary:
    return escape(id_dictionary[element.name])
  else:
    return '[No value]'


    
    
    