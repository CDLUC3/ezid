# =============================================================================
#
# EZID :: datacite_xml.py
#
# Allows processing a form with form elements named with simple XPATH
# expressions 
# 1) Generates form fields for use with Django form model.
# 2) Creates an XML document for attaching Datacite XML metadata.
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
  "contributors", "dates", "alternateIdentifiers", "relatedIdentifiers", "sizes",
  "formats", "rightsList", "descriptions", "geoLocations", "fundingReferences"]

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

    creators-creator-1-nameIdentifier-schemeURI

  Repeatable elements are indexed at the top level only; lower-level
  repeatable elements (e.g., contributor affiliations) are
  concatenated.  One exception to the above rule is that the key for
  the content of a top-level repeatable element carries an extra
  component that echoes the element name, as in:

    creators-creator-0-creator
    creators-creator-1-creator

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
            if mypathx in d:
              # Repeatable elements not explicitly handled have their
              # content concatenated.
              d[mypathx] += " ; " + v
            else:
              d[mypathx] = v
  root = util.parseXmlString(document)
  for c in getElementChildren(root): processNode("", c)
  fc = _separateByFormType(d)
  return fc 

def _separateByFormType(d):
  """ Organize form elements into a manageable collection 
      Turn empty dicts into None so that forms render properly

      Nonrepeating fields (fields that can't be repeated into multiple forms) are: 
         identifier, identifier-identifierType, language, publisher, publicationYear, version
  """
  _nonRepeating = {k:v for (k,v) in d.iteritems() 
    if not any(e in k for e in _repeatableElementContainers) and not k.startswith('resourceType')}

  def dict_generate(d, s):
    dr = {k:v for (k,v) in d.iteritems() if k.startswith(s)}
    return dr if dr else None

  """ Representation of django forms and formsets used for DataCite XML """
  FormColl = collections.namedtuple('FormColl', 'nonRepeating resourceType creators titles descrs subjects contribs dates altids relids sizes formats rights geoLocations fundingReferences')

  return FormColl(
    nonRepeating=_nonRepeating if _nonRepeating else None, 
    resourceType = dict_generate(d, 'resourceType'),
    creators = dict_generate(d, 'creators'),
    titles = dict_generate(d, 'titles'),
    descrs = dict_generate(d, 'descriptions'),
    subjects = dict_generate(d, 'subjects'),
    contribs = dict_generate(d, 'contributors'),
    dates = dict_generate(d, 'dates'),
    altids = dict_generate(d, 'alternateIdentifiers'),
    relids = dict_generate(d, 'relatedIdentifiers'),
    sizes = dict_generate(d, 'sizes'),
    formats = dict_generate(d, 'formats'),
    rights = dict_generate(d, 'rightsList'),
    geoLocations = dict_generate(d, 'geoLocations'),
    fundingReferences = dict_generate(d, 'fundingReferences')
  )

def temp_mockxml():
  return unicode('<resource xmlns="http://datacite.org/schema/kernel-3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-3 http://schema.datacite.org/meta/kernel-3/metadata.xsd"><identifier identifierType="ARK"/><creators><creator><creatorName>test</creatorName><givenName>Elizabeth</givenName><familyName>Miller</familyName><affiliation>DataCite</affiliation><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0007</nameIdentifier></creator></creators><titles><title xml:lang="en-us">test</title></titles><publisher>test</publisher><publicationYear>1990</publicationYear><subjects><subject xml:lang="ar-afb" schemeURI="testURI" subjectScheme="testScheme">TESTTESTTESTTEST</subject><subject xml:lang="en" subjectScheme="testScheme2" schemeURI="testURI2">test2</subject></subjects><resourceType resourceTypeGeneral="Dataset">Dataset</resourceType><descriptions><description xml:lang="es-419" descriptionType="Abstract">testDescr</description><description xml:lang="zh-Hans" descriptionType="Other">testDescr2</description><description xml:lang="ast" descriptionType="SeriesInformation">testDescr3</description></descriptions></resource>')

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
  "contributors", "contributor", "contributorName", "givenName", "familyName",
  "nameIdentifier_0", "nameIdentifier_1", "affiliation_0", "affiliation_1", "dates",
  "date", "language", "resourceType", "alternateIdentifiers", "alternateIdentifier",
  "relatedIdentifiers", "relatedIdentifier", "sizes", "size", "formats", "format",
  "version", "rightsList", "rights", "descriptions", "description", "geoLocations",
  "geoLocation", "geoLocationPoint", "geoLocationBox", "westBoundLongitude",
  "eastBoundLongitude", "southBoundLatitude", "northBoundLatitude", "geoLocationPlace",
  "geoLocationPolygon", "pointLongitude", "pointLatitude", "fundingReferences",
  "fundingReference", "funderName", "funderIdentifier", "awardNumber", "awardTitle"]

_elements = dict((e, i) for i, e in enumerate(_elementList))

def formElementsToDataciteXml (d, shoulder=None, identifier=None):
  """
  The inverse of dataciteXmlToFormElements.
  First, filter for only DataCite XML items. Remove unnecessary Django form variables
      i.e.  (u'titles-title-MAX_NUM_FORMS', u'1000')
      Also remove other fields from query object not related to datacite_xml fields
      i.e.  (u'action', u'create') 
  """
  d = {k:v for (k,v) in d.iteritems() if '_FORMS' not in k}
  d = {k:v for (k,v) in d.iteritems() if any(e in k for e in _elementList)}
  d = _addIdentifierInfo(d, shoulder, identifier)
  namespace = "http://datacite.org/schema/kernel-4"
  schemaLocation = "http://schema.datacite.org/meta/kernel-4/metadata.xsd"
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
          i, remainder = remainder.split("-", 1)
          i = int(i)
          while len(node) <= i: lxml.etree.SubElement(node, q(k))
          node = node[i]
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
  def stripNumberedElements (node):
    nn = {'nameIdentifier_0': ['nameIdentifierScheme_0', 'schemeURI_0'],
         'nameIdentifier_1': ['nameIdentifierScheme_1', 'schemeURI_1'],
         'affiliation_0': [], 'affiliation_1': []}
    for k in nn:
      e = node.find('.//'+q(k)) 
      e.tag = q(k)[:-2]     # strip underscore and number off element tag 
      # Rename attributes as well (create a clone with new name)
      for x in range(len(nn[k])):
        value = e.get(nn[k][x])
        e.set(nn[k][x][:-2], value)
        e.attrib.pop(nn[k][x])
  stripNumberedElements(root)
  return lxml.etree.tostring(root, encoding=unicode)


def _addIdentifierInfo(d, shoulder=None, identifier=None):
  if shoulder is None:
    assert identifier
    id_str = identifier
  else: id_str = shoulder
  d['identifier-identifierType'] = _id_type(id_str)        # Required
  if identifier is not None: d['identifier'] = identifier  # Only for already created IDs
  return d

def temp_mockFormElements():
  return {u'subjects-subject-0-subject': u'', u'creators-creator-0-affiliation-3-affiliation': u'', u'subjects-subject-0-schemeURI': u'', u'descriptions-description-0-descriptionType': u'', u'subjects-subject-0-subjectScheme': u'', u'fundingReferences-fundingReference-0-funderName': u'', u'creators-creator-0-creatorName-0-creatorName': u'test', u'creators-creator-0-nameIdentifier-4-nameIdentifier': u'', u'fundingReferences-fundingReference-0-awardURI': u'', u'contributors-contributor-0-givenName-1-givenName': u'', u'contributors-contributor-0-contributorName': u'', u'contributors-contributor-0-nameIdentifier-schemeURI': u'', u'formats-format-0-format': u'', u'geoLocations-geoLocation-0-geoLocationBox': u'', u'sizes-size-0-size': u'', u'fundingReferences-fundingReference-0-funderIdentifierType': u'', u'contributors-contributor-0-nameIdentifier-nameIdentifierScheme': u'', u'descriptions-description-0-description': u'', u'relatedIdentifiers-relatedIdentifier-0-relatedIdentifier': u'', u'resourceType-resourceTypeGeneral': u'Dataset', u'titles-title-0-titleType': u'', u'version': u'', u'titles-title-0-title': u'test', u'titles-title-0-{http://www.w3.org/XML/1998/namespace}lang': u'', u'alternateIdentifiers-alternateIdentifier-0-alternateIdentifierType': u'', u'fundingReferences-fundingReference-0-awardTitle': u'', u'contributors-contributor-0-contributorType': u'', u'relatedIdentifiers-relatedIdentifier-0-relatedIdentifierType': u'', u'contributors-contributor-0-affiliation': u'', u'subjects-subject-0-valueURI': u'', u'creators-creator-0-nameIdentifier-4-nameIdentifierScheme': u'', u'publisher': u'tets', u'dates-date-0-date': u'', u'contributors-contributor-0-familyName-2-familyName': u'Rorschenbach', u'geoLocations-geoLocation-0-geoLocationPoint': u'', u'subjects-subject-0-{http://www.w3.org/XML/1998/namespace}lang': u'', u'alternateIdentifiers-alternateIdentifier-0-alternateIdentifier': u'', u'dates-date-0-dateType': u'', u'relatedIdentifiers-relatedIdentifier-0-schemeType': u'', u'fundingReferences-fundingReference-0-awardNumber': u'', u'descriptions-description-0-{http://www.w3.org/XML/1998/namespace}lang': u'', u'contributors-contributor-0-nameIdentifier': u'', u'geoLocations-geoLocation-0-geoLocationPlace': u'', u'fundingReferences-fundingReference-0-funderIdentifier': u'', u'publicationYear': u'1999', u'language': u'', u'resourceType': u'Dataset', u'creators-creator-0-nameIdentifier-4-schemeURI': u'', u'relatedIdentifiers-relatedIdentifier-0-relatedMetadataScheme': u'', u'relatedIdentifiers-relatedIdentifier-0-schemeURI': u'', u'relatedIdentifiers-relatedIdentifier-0-relationType': u'', u'rightsList-rights-0-rights': u'', u'rightsList-rights-0-rightsURI': u'', u'creators-creator-0-familyName-2-familyName': u'', u'creators-creator-0-givenName-1-givenName': u'SmartyPants'}
