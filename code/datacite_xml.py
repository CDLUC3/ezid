# =============================================================================
#
# EZID :: datacite_xml.py
#
# Allows processing a form with form elements named with simple XPATH
# expressions and creates an XML document for attaching Datacite XML
# metadata.
#
# Author:
#   Scott Fisher <sfisher@ucop.edu>
#
# License:
#   Copyright (c) 2010, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

from lxml import etree
import re

def generate_xml(param_items):
  """This generates and returns a limited datacite XML 2.2 document from form items.
  Pass in something like request.POST.items(), for example."""
  r = etree.fromstring('<resource xmlns="http://datacite.org/schema/kernel-2.2"' + \
                       ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"' + \
                       ' xsi:schemaLocation="http://datacite.org/schema/kernel-2.2' + \
                       ' http://schema.datacite.org/meta/kernel-2.2/metadata.xsd"/>')

  items = [x for x in param_items if x[0].startswith("/resource") ]
  RESOURCE_ORDER = ["/resource/" + x for x in ['creators', 'titles', 'publisher', 'publicationYear', 'subjects', 
                    'contributors', 'dates', 'language', 'resourceType', 'alternateIdentifiers',
                    'relatedIdentifiers', 'rights', 'descriptions'] ]
  items = sorted(items, key=lambda i: i[0]) #sort by element name
  #sort by ordinal(s) in string, this may not work all complex cases but should work for datacite
  items = sorted(items, key=lambda i: _sort_get_ordinal(i[0])) 
  items = sorted(items, key=lambda i: RESOURCE_ORDER.
                 index(re.search('^/resource/[a-zA-Z0-9\[\]]+', i[0]).group())) #sort in preferred order of sections

  for k, v in items:
    if v != '':
      _create_xml_element(r, k, v)
    
  return etree.tostring(r, pretty_print=True)

def _create_xml_element(root_el, path, value):
  """ creates xml element """
  split_path = path.split("/")[1:]
  if split_path[0] == _remove_ns(root_el.tag):
    split_path = split_path[1:]
  _xml_create(root_el, split_path, value)
  
def _xml_create(base_el, path_arr, value):
  #create or check element here
  tag = path_arr[0]
  simple_tag = _remove_at(_remove_ordinal(tag))
  children = _children_w_tag(base_el, simple_tag)
  if _is_attribute(tag):
    #set an attribute
    if len(path_arr) > 1:
      #this shouldn't happen
      return
    else:
      base_el.set(simple_tag, value)
  else:
    if _has_ordinal(tag):
      ord = _get_ordinal(tag) - 1 #must subtract one because form ordinals start at 1, not 0
    else:
      ord = 0  #no ordinal, then it's effectively an ordinal of the first [0]
    if ord > len(children) - 1:
      child = etree.Element(simple_tag)
      base_el.append(child)
    else:
      child = children[ord]
    if len(path_arr) == 1:
      child.text = value  #leaf node, so set value
    else:
      _xml_create(child, path_arr[1:], value) #not leaf node, so recurse for more path

def _remove_ns(str):
  """ removes the horrifying namespace uri from string so can compare easily"""
  return re.sub(r'^{[^}]+}', '', str)

def _children_w_tag(base, tag):
  return [ child for child in base.iter(tag) ]
  #was [child for child in base if _remove_ns(child.tag) == tag ]

def _remove_ordinal(str):
  """removes the ordinal like [1] from path element"""
  return re.sub(r'\[[0-9]+\]$', '', str)

def _has_ordinal(str):
  """sees if it has an ordinal like [1] at end of element"""
  return str.endswith("]")

def _get_ordinal(str):
  """gets the ordinal at end of element string like [1] and returns an integer"""
  return int(re.search('\[([0-9]+)\]$', str).group(1))

def _is_attribute(str):
  """sees if this element string is an attribute"""
  return str.startswith("@")

def _remove_at(str):
  """removes an @ sign at beginning of string if it exists"""
  return re.sub(r'^@', '', str)

def _sort_get_ordinal(str):
  """gets the ordinal(s) in the element string, if it doesn't have any return [0]"""
  m = re.compile('\[([0-9]+)\]')
  if m.search(str) == None:
    return [0]
  else:
    return [int(x) for x in m.findall(str)]