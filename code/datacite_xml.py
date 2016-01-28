# =============================================================================
#
# EZID :: datacite_xml.py
#
# Allows processing a form with form elements named with simple XPATH
# expressions 
# 1) Generates form fields for use with Django form model.
# 2) Creates an XML document for attaching Datacite XML metadata.
#
# Authors:
#   Scott Fisher <sfisher@ucop.edu>, Greg Janee <gjanee@ucop.edu> 
#
# License:
#   Copyright (c) 2016, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import lxml.etree
import util
import re
import copy
import collections

_repeatableElementContainers = ["creators", "titles", "subjects",
  "contributors", "dates", "alternateIdentifiers", "relatedIdentifiers",
  "sizes", "formats", "rightsList", "descriptions", "geoLocations"]

def dataciteXmlToFormElements (document):
  """
  Converts a DataCite XML record to a dictionary of form elements.
  All non-content (comments, etc.) is discarded.  Whitespace is
  processed and empty element and attribute values are discarded.
  Dictionary keys follow the pattern of element and attribute XPaths,
  e.g., the schemeURI attribute in the following XML fragment:

    <resource>
      <creators>
        <creator>...</creator>
        <creator>
          <nameIdentifier schemeURI="...">

  is identified by key:

    creators-creator-2-nameIdentifier-schemeURI

  Repeatable elements are indexed at the top level only; lower-level
  repeatable elements (e.g., contributor affiliations) are
  concatenated.  One exception to the above rule is that the key for
  the content of a top-level repeatable element carries an extra
  component that echoes the element name, as in:

    creators-creator-2-creator

  <br> elements in descriptions are replaced with newlines.
  """
  d = {}
  def tagName (tag):
    return tag.split("}")[1]
  def getElementChildren (node):
    return list(node.iterchildren(lxml.etree.Element))
  def getText (node):
    t = node.text or ""
    for c in node.iterchildren(): t += c.tail or ""
    return t
  def processNode (path, node, index=None):
    tag = tagName(node.tag)
    if path == "":
      mypath = tag
    else:
      mypath = "%s-%s" % (path, tag)
    if index != None:
      mypath += "-%d" % index
      mypathx = "%s-%s" % (mypath, tag)
    else:
      mypathx = mypath
    for a in node.attrib:
      v = node.attrib[a].strip()
      if v != "": d["%s-%s" % (mypath, a)] = v
    if tag in _repeatableElementContainers:
      for i, c in enumerate(getElementChildren(node)):
        processNode(mypath, c, i)
    else:
      if tag == "description":
        # The only mixed-content element type in the schema; <br>'s
        # get replaced with newlines.
        v = node.text or ""
        for c in node.iterchildren():
          if isinstance(c.tag, basestring) and tagName(c.tag) == "br":
            v += "\n"
          v += c.tail or ""
        v = v.strip()
        if v != "": d[mypathx] = v
      else:
        children = getElementChildren(node)
        if len(children) > 0:
          for c in children: processNode(mypath, c)
        else:
          v = getText(node).strip()
          if v != "":
            if mypath in d:
              # Repeatable elements not explicitly handled have their
              # content concatenated.
              d[mypathx] += " ; " + v
            else:
              d[mypathx] = v
  root = util.parseXmlString(document)
  for c in getElementChildren(root): processNode("", c)
  fc = _separateByFormType(d)
  return fc 

""" Representation of django forms and formsets used for DataCite XML """
FormColl = collections.namedtuple('FormColl', 'nonRepeating resourceType creators titles geoLocations')

def _separateByFormType(d):
  """ Organize form elements into a manageable collection 
      Turn empty dicts into None so that forms render properly
  """
  _nonRepeating = {k:v for (k,v) in d.iteritems() 
    if not any(e in k for e in _repeatableElementContainers) and not k.startswith('resourceType')}
  _resourceType = {k:v for (k,v) in d.iteritems() if k.startswith('resourceType')}
  _creators = {k:v for (k,v) in d.iteritems() if k.startswith('creators')}
  _titles = {k:v for (k,v) in d.iteritems() if k.startswith('titles')}
  _geoLocations = {k:v for (k,v) in d.iteritems() if k.startswith('geoLocations')}
  return FormColl(
    nonRepeating=_nonRepeating if _nonRepeating else None, 
    resourceType=_resourceType if _resourceType else None,
    creators=_creators if _creators else None, 
    titles=_titles if _titles else None, 
    geoLocations=_geoLocations if _geoLocations else None
  )

def temp_mock():
  return unicode('<resource xmlns="http://datacite.org/schema/kernel-3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-3 http://schema.datacite.org/meta/kernel-3/metadata.xsd"><identifier identifierType="ARK"/><creators><creator><creatorName>test</creatorName><nameIdentifier schemeURI="" nameIdentifierScheme=""></nameIdentifier><affiliation></affiliation></creator><creator><creatorName>test2</creatorName><nameIdentifier schemeURI="" nameIdentifierScheme="">testNameId</nameIdentifier><affiliation>testAffiliation</affiliation></creator></creators><titles><title titleType=""><title>test</title></title></titles><publisher>test</publisher><publicationYear>1990</publicationYear><geoLocations><geoLocation><geoLocationPoint></geoLocationPoint><geoLocationBox></geoLocationBox><geoLocationPlace></geoLocationPlace></geoLocation></geoLocations></resource>')
def temp_mock2():
  return unicode('<resource xmlns="http://datacite.org/schema/kernel-3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-3 http://schema.datacite.org/meta/kernel-3/metadata.xsd"><identifier identifierType="ARK"/><creators><creator><creatorName>test</creatorName><nameIdentifier schemeURI="" nameIdentifierScheme=""></nameIdentifier><affiliation></affiliation></creator><creator><creatorName>test2</creatorName><nameIdentifier schemeURI="" nameIdentifierScheme="">testNameId</nameIdentifier><affiliation>testAffiliation</affiliation></creator></creators><titles><title titleType=""><title>test</title></title></titles><publisher>test</publisher><publicationYear>1990</publicationYear><resourceType resourceTypeGeneral="Dataset"></resourceType><geoLocations><geoLocation><geoLocationPoint></geoLocationPoint><geoLocationBox></geoLocationBox><geoLocationPlace></geoLocationPlace></geoLocation></geoLocations></resource>')

def _id_type(str):
  m = re.compile("^[a-z]+")
  if m.search(str) == None:
    return u''
  else:
    return m.findall(str)[0].upper()

# The following exhaustive list of DataCite XML elements must form a
# partial topological order, that is, if two elements have the same
# parent, they must appear in the list in the same order that they
# must appear in an XML document.

_elementList = ["identifier", "creators", "creator", "creatorName",
  "titles", "title", "publisher", "publicationYear", "subjects", "subject",
  "contributors", "contributor", "contributorName", "nameIdentifier",
  "affiliation", "dates", "date", "language", "resourceType",
  "alternateIdentifiers", "alternateIdentifier", "relatedIdentifiers",
  "relatedIdentifier", "sizes", "size", "formats", "format", "version",
  "rightsList", "rights", "descriptions", "description", "geoLocations",
  "geoLocation", "geoLocationPoint", "geoLocationBox", "geoLocationPlace"]

_elements = dict((e, i) for i, e in enumerate(_elementList))

def formElementsToDataciteXml (d, shoulder, identifier=None):
  """
  The inverse of dataciteXmlToFormElements.
  First, filter for only DataCite XML items. Remove unnecessary Django form variables
      i.e.  (u'titles-title-MAX_NUM_FORMS', u'1000')
      Also remove other fields from query object not related to datacite_xml fields
      i.e.  (u'action', u'create') 
  """
  d = {k:v for (k,v) in d.iteritems() if '_FORMS' not in k}
  d = {k:v for (k,v) in d.iteritems() if any(e in k for e in _elementList)}
  d['identifier-identifierType'] = _id_type(shoulder)
  if identifier is not None: d['identifier'] = identifier
  namespace = "http://datacite.org/schema/kernel-3"
  schemaLocation = "http://schema.datacite.org/meta/kernel-3/metadata.xsd"
  def q (elementName):
    return "{%s}%s" % (namespace, elementName)
  def tagName (tag):
    return tag.split("}")[1]
  root = lxml.etree.Element(q("resource"), nsmap={ None: namespace })
  root.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"] =\
    namespace + " " + schemaLocation
  for key, value in d.items():
    value = value.strip()
    if value == "": continue
    node = root
    while len(key) > 0:
      k, remainder = key.split("-", 1) if "-" in key else (key, "")
      if k in _elements:
        if tagName(node.tag) in _repeatableElementContainers:
          i, remainder = remainder.split("-", 1) if "-" in remainder else\
            (remainder, "")
          i = int(i) + 1
          while len(node) < i: lxml.etree.SubElement(node, q(k))
          node = node[i-1]
          if remainder == k: remainder = ""
        else:
          n = node.find(q(k))
          if n != None:
            node = n
          else:
            node = lxml.etree.SubElement(node, q(k))
        if remainder == "": node.text = value
      else:
        node.attrib[k] = value
      key = remainder
  def sortChildren (node):
    if tagName(node.tag) not in _repeatableElementContainers:
      children = node.getchildren()
      children.sort(key=lambda c: _elements[tagName(c.tag)])
      for i, c in enumerate(children): node.insert(i, c)
    for c in node.iterchildren(): sortChildren(c)
  sortChildren(root)
  return lxml.etree.tostring(root, encoding=unicode)

# ToDo: remove rest of this, I believe it's no longer needed 
# ============================================================================= 
#   XML generation
# =============================================================================

# Order for XML elements. Schema specifies a sequence in some cases (geoLocations).
RESOURCE_ORDER = ['resource', 'creators', 'creator', 'creatorName',
  'titles', 'publisher', 'publicationYear', 'language', 'version', 'resourceType',
  'descriptions', '@descriptionType', 'subjects', '@subjectScheme', 'contributors', 
  'contributorName', '@contributorType', 'formats', 'dates', 'alternateIdentifiers',
  'relatedIdentifiers', '@relationType', '@relatedIdentifierType', '@relatedMetadataScheme', 
  '@schemeType', 'rightsList', '@rightsURI', 'sizes', 'geoLocations',
  # This order is important 
  'geoLocationPoint', 'geoLocationBox', 'geoLocationPlace', 
  # it's important that nameIdentifier comes after contributorName
  'nameIdentifier', '@nameIdentifierScheme', '@schemeURI','affiliation']

def splitPath (p):
  # Splits the first "chunk" off an xpath:
  # "/x/y" -> ("x", "/y")
  # "/x[n]/y" -> ("x", "[n]/y")
  # "[n]/y" -> (n, "/y")
  # "/x" -> ("x", "")
  # "[n]" -> (n, "")
  if p.startswith("/"):
    m = re.match("/([^/\[]+)", p)
    return (m.group(1), p[len(m.group(0)):])
  else:
    m = re.match("\[([^\]]*)\]", p)
    return (int(m.group(1)), p[len(m.group(0)):])

def compareXpaths (a, b):
  while len(a) > 0 and len(b) > 0:
    if a.startswith("/") and b.startswith("/"):
      x, a = splitPath(a)
      y, b = splitPath(b)
      if x != y: return cmp(RESOURCE_ORDER.index(x), RESOURCE_ORDER.index(y))
    elif a.startswith("[") and b.startswith("["):
      m, a = splitPath(a)
      n, b = splitPath(b)
      if m != n: return cmp(m, n)
    else:
      return cmp(a, b)
  return cmp(a, b)

# Description element has a decriptionType attribute which is automatically
#   populated in the template. Remove this element if description itself is empty.
# Just doing this for the first instance
def _removeEmptyDescriptions(items):
  index_descr = [x[0] for x in items].index(u'/resource/descriptions/description[1]') 
  index_descrType = (
    [x[0] for x in items].index(u'/resource/descriptions/description[1]/@descriptionType') 
  )
  if re.match("^\s*$", items[index_descr][1]):
    del items[index_descr]
    del items[index_descrType]
  return items

# this section generates the XML document based on form with XPATH expressions
def generate_xml(param_items):
  """This generates and returns a limited datacite XML document from form items.
  Pass in something like request.POST, for example.  Required elements are
  at least one creator, title, publisher and publicationYear"""
  r = etree.fromstring(u'<resource xmlns="http://datacite.org/schema/kernel-3"' + \
                       u' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"' + \
                       u' xsi:schemaLocation="http://datacite.org/schema/kernel-3' + \
                       u' http://schema.datacite.org/meta/kernel-3/metadata.xsd"/>')
  items = [x for x in param_items.items() if x[0].startswith(u"/resource") ]
  items = _removeEmptyDescriptions(items)
  items = sorted(items, cmp=compareXpaths, key=lambda i: i[0])

  if (param_items['action'] and param_items['action'] == 'create'):
    id_type = _id_type(param_items[u'shoulder'])
  else:
    _create_xml_element(r, u'/resource/identifier', param_items[u'identifier']) 
    id_type = _id_type(param_items[u'identifier'])
  _create_xml_element(r, u'/resource/identifier/@identifierType', id_type) #must create empty element and specify type to mint

  for k, v in items:
    if v != u'':
      _create_xml_element(r, k, v)
  return u"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" + \
    etree.tostring(r, encoding=unicode, method="xml", pretty_print=True)

def _create_xml_element(root_el, path, value):
  """ creates xml element """
  split_path = path.split(u"/")[1:]
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
  return re.sub(r'^{[^}]+}', u'', str)

def _children_w_tag(base, tag):
  return [ child for child in base.iter(tag) ]
  #was [child for child in base if _remove_ns(child.tag) == tag ]

def _remove_ordinal(str):
  """removes the ordinal like [1] from path element"""
  return re.sub(r'\[[0-9]+\]$', u'', str)

def _has_ordinal(str):
  """sees if it has an ordinal like [1] at end of element"""
  return str.endswith(u"]")

def _get_ordinal(str):
  """gets the ordinal at end of element string like [1] and returns an integer"""
  return int(re.search('\[([0-9]+)\]$', str).group(1))

def _is_attribute(str):
  """sees if this element string is an attribute"""
  return str.startswith(u"@")

def _remove_at(str):
  """removes an @ sign at beginning of string if it exists"""
  return re.sub(r'^@', u'', str)

def _sort_get_ordinal(str):
  """gets the ordinal(s) in the element string, if it doesn't have any return [0]"""
  m = re.compile('\[([0-9]+)\]')
  if m.search(str) == None:
    return [0]
  else:
    return [int(x) for x in m.findall(str)]
  
def validate_document(xml_doc, xsd_path, err_msgs):
  """Validates the document against the XSD and adds
  error messages to the err_msgs array if things go wrong"""
  p = re.compile(r'(<\?xml.+?)(encoding="UTF-8")(.*?\?>)')
  cleansed_xml = p.sub(r'\1\3', xml_doc)
  p = re.compile(r'(<resource.+?)(xsi:schemaLocation=".+?")(.*?>)')
  cleansed_xml = p.sub(r'\1\3', cleansed_xml)
  xsd_doc = etree.parse(xsd_path)
  xsd = etree.XMLSchema(xsd_doc)
  parser = etree.XMLParser(ns_clean=True, recover=True)
  xml = etree.fromstring(cleansed_xml, parser)
  
  # must add something like <identifier identifierType="DOI">10.5072/FK25Q56C6</identifier>
  # because it will not validate until it's present, even though we haven't minted
  # an identifier yet, but want to validate as though we had
  el = xml.find('{http://datacite.org/schema/kernel-3}identifier')
  el.attrib['identifierType'] = 'DOI'
  el.text = '10.5072/FK25Q56C6'
  if not xsd.validate(xml):
    #err_msgs.append("XML validation errors occurred for the values you entered:")
    simple_errors = [re.sub("\\{http://[^ ]+?\\}", '', x.message) for x in xsd.error_log] #removes namespace crap
    err_msgs.extend(_translate_errors(simple_errors))
    return False
  return True


"""Lists of errors for error translation from lxml/libxml2 to the interface"""
EXACT_ERRS = {"Element 'contributor': The attribute 'contributorType' is required but missing.":
    "Contributor Type is required if you fill in contributor information.",
  "Element 'description': The attribute 'descriptionType' is required but missing.":
    "If descriptive information is present in the Abstract section, a type must be selected.",
  "Element 'contributor': Missing child element(s). Expected is ( contributorName ).":
    "Contributor Name is required if you fill in contributor information.",
  "Element 'nameIdentifier': This element is not expected. Expected is ( contributorName ).":
    "Contributor Name is required if you fill in contributor information.",
  "Element 'date': The attribute 'dateType' is required but missing.":
    "Date Type is required if you fill in a Date.",
  "Element 'alternateIdentifier': The attribute 'alternateIdentifierType' is required but missing.":
    "The Alternate Identifier Type is required if you fill in an Alternate Identifier.",
  "Element 'relatedIdentifier': The attribute 'relatedIdentifierType' is required but missing.":
    "The Related Identifier Type is required if you fill in a Related Identifier.",
  "Element 'relatedIdentifier': The attribute 'relationType' is required but missing.":
    "Relation Type is required if you fill in a Related Identifier.",
  "Element 'geoLocationPoint': [facet 'minLength'] The value has a length of '1'; this underruns the allowed minimum length of '2'.":
    "Geolocation points must be made up of two numbers separated by a space.",
  "Element 'resourceType': The attribute 'resourceTypeGeneral' is required but missing.":
    "A Resource Type is required if you fill in the Resource Type Description.",
  "Element 'nameIdentifier': The attribute 'nameIdentifierScheme' is required but missing.":
    "An Identifier Scheme must be filled in if you specify a Scheme URI.",
  "Element 'nameIdentifier': '' is not a valid value of the atomic type 'nonemptycontentStringType'.":
    "A Name Identifier must be filled in if you specify an Identifier Scheme or Scheme URI.",
  "Element 'nameIdentifier': [facet 'minLength'] The value has a length of '0'; this underruns the allowed minimum length of '1'.":
    ""}
  
REGEX_ERRS = {r"^Element 'geoLocationPoint': '.+?' is not a valid value of the atomic type 'xs:double'\.$":
    'A Geolocation Point must use only decimal numbers for longitude and latitude.',
  r"^Element 'geoLocationPoint': '.+?' is not a valid value of the list type 'point'\.$":
    '',
  r"^Element 'geoLocationPoint': \[facet 'maxLength'\] The value has a length of '.+?'; this exceeds the allowed maximum length of '2'\.$":
    'Geolocation points must be made up of two numbers separated by a space.',
  r"^Element 'geoLocationBox': \[facet 'minLength'\] The value has a length of '.+?'; this underruns the allowed minimum length of '4'\.$":
    'A Geolocation Box must contain 4 numbers separated by spaces.',
  r"^Element 'geoLocationBox': \[facet 'maxLength'\] The value has a length of '5'; this exceeds the allowed maximum length of '4'\.$":
    'A Geolocation Box must contain 4 numbers separated by spaces.',
  r"^Element 'geoLocationBox': '.+?' is not a valid value of the list type 'box'\.$":
    '',
  r"^Element 'geoLocationBox': '.+?' is not a valid value of the atomic type 'xs:double'\.$":
    'A Geolocation Box must use only decimal numbers for longitudes and latitudes.'
  }

def _translate_errors(err_in):
  """translates the errors returned by lxml and libxml2 after validation into more
  readable errors for users.  If no translation, then passes it through"""
  errs_copy = copy.copy(err_in)
  errs_out = []
  
  # add translation of any exact errors
  for key, value in EXACT_ERRS.iteritems():
    if key in errs_copy:
      errs_out.append(value)
      errs_copy.remove(key)
      
  # add translation of any regex matches for errors
  temp_trans = {}
  for err in errs_copy:
    for key, value in REGEX_ERRS.iteritems():
      a = re.compile(key)
      if a.match(err):
        temp_trans[err] = value
        break
  
  for key, value in temp_trans.iteritems():
    errs_out.append(value)
    errs_copy.remove(key)
 
  # add any untranslated errors
  for err in errs_copy:
    errs_out.append(err)
  return list(set([x for x in errs_out if x]))
