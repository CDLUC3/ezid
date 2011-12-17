from django import template

register = template.Library()

@register.simple_tag
def display_value(meta_dict, el):
  """Takes the id metadata dictionary and profile element.
  This will probably become more complicated since different profile data types may format differently, etc."""
  if el.name in meta_dict:
    return meta_dict[el.name]
  else:
    return '[No value]'