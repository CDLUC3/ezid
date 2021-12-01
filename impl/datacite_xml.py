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

import datacite
import geometry_util

_repeatableElementContainers = [
    "creators",
    "titles",
    "subjects",
    "contributors",
    "dates",
    "alternateIdentifiers",
    "relatedIdentifiers",
    "sizes",
    "formats",
    "rightsList",
    "descriptions",
    "geoLocations",
    "fundingReferences",
]

_numberedElementContainers = {
    "creator": ["nameIdentifier"],
    "contributor": ["nameIdentifier"],
}

_maxNumberedElements = 2


def dataciteXmlToFormElements(document):
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

    creators-creator-1-nameIdentifier_0-schemeURI

  Repeatable elements are indexed at the top level only; lower-level
  repeatable elements (e.g., contributor affiliations) are
  concatenated.  However, certain repeatable elements (see
  _numberedElementContainers), such as nameIdentifier in the example
  above, are indexed, but with underscores.  An additional tweak to
  the naming pattern is that the key for the content of a top-level
  repeatable element carries an extra component that echoes the
  element name, as in:

    alternateIdentifiers-alternateIdentifier-0-alternateIdentifier
    alternateIdentifiers-alternateIdentifier-1-alternateIdentifier

  <br> elements in descriptions are replaced with newlines.
  """
    document = datacite.upgradeDcmsRecord(document)
    d = {}

    def tagName(tag):
        return tag.split("}")[1]

    def getElementChildren(node):
        return list(node.iterchildren(lxml.etree.Element))

    def getText(node):
        t = node.text or ""
        for c in node.iterchildren():
            t += c.tail or ""
        return t

    def processNode(path, node, index=None, separator="-"):
        tag = tagName(node.tag)
        if path == "":
            mypath = tag
        else:
            mypath = "%s-%s" % (path, tag)
        if index != None:
            mypath += "%s%d" % (separator, index)
            mypathx = "%s-%s" % (mypath, tag)
        else:
            mypathx = mypath
        for a in node.attrib:
            v = node.attrib[a].strip()
            if v != "":
                d["%s-%s" % (mypath, a)] = v
        if tag in _repeatableElementContainers:
            for i, c in enumerate(getElementChildren(node)):
                processNode(mypath, c, i)
        elif tag in _numberedElementContainers:
            indexes = {t: -1 for t in _numberedElementContainers[tag]}
            for c in getElementChildren(node):
                if tagName(c.tag) in indexes:
                    indexes[tagName(c.tag)] += 1
                    processNode(mypath, c, indexes[tagName(c.tag)], separator="_")
                else:
                    processNode(mypath, c)
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
                if v != "":
                    d[mypathx] = v
            elif tag == "geoLocationPolygon":
                d[mypathx] = geometry_util.datacitePolygonToInternal(node)
            else:
                children = getElementChildren(node)
                if len(children) > 0:
                    for c in children:
                        processNode(mypath, c)
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
    for c in getElementChildren(root):
        processNode("", c)
    fc = _separateByFormType(d)
    return fc


def _separateByFormType(d):
    """ Organize form elements into a manageable collection 
      Turn empty dicts into None so that forms render properly

      Nonrepeating fields (fields that can't be repeated into multiple forms) are: 
         identifier, identifier-identifierType, language, publisher, publicationYear, version
  """
    _nonRepeating = {
        k: v
        for (k, v) in d.iteritems()
        if not any(e in k for e in _repeatableElementContainers)
        and not k.startswith('resourceType')
    }

    def dict_generate(d, s):
        dr = {k: v for (k, v) in d.iteritems() if k.startswith(s)}
        return dr if dr else None

    """ Representation of django forms and formsets used for DataCite XML """
    FormColl = collections.namedtuple(
        'FormColl',
        'nonRepeating resourceType creators titles descrs subjects contribs dates altids relids sizes formats rights geoLocations fundingReferences',
    )

    return FormColl(
        nonRepeating=_nonRepeating if _nonRepeating else None,
        resourceType=dict_generate(d, 'resourceType'),
        creators=dict_generate(d, 'creators'),
        titles=dict_generate(d, 'titles'),
        descrs=dict_generate(d, 'descriptions'),
        subjects=dict_generate(d, 'subjects'),
        contribs=dict_generate(d, 'contributors'),
        dates=dict_generate(d, 'dates'),
        altids=dict_generate(d, 'alternateIdentifiers'),
        relids=dict_generate(d, 'relatedIdentifiers'),
        sizes=dict_generate(d, 'sizes'),
        formats=dict_generate(d, 'formats'),
        rights=dict_generate(d, 'rightsList'),
        geoLocations=dict_generate(d, 'geoLocations'),
        fundingReferences=dict_generate(d, 'fundingReferences'),
    )


def temp_mockxml():
    # An item whose Creator has two nameIDs and two affiliations
    # return unicode('<resource xmlns="http://datacite.org/schema/kernel-3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-3 http://schema.datacite.org/meta/kernel-3/metadata.xsd"><identifier identifierType="ARK"/><creators><creator><creatorName>test</creatorName><givenName>Elizabeth</givenName><familyName>Miller</familyName><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/2" nameIdentifierScheme="ORCID2">0000-0001-5000-0002</nameIdentifier><affiliation>DataCite1</affiliation><affiliation>DataCite2</affiliation></creator></creators><titles><title xml:lang="en-us">test</title></titles><publisher>test</publisher><publicationYear>1990</publicationYear><subjects><subject xml:lang="ar-afb" schemeURI="testURI" subjectScheme="testScheme">TESTTESTTESTTEST</subject><subject xml:lang="en" subjectScheme="testScheme2" schemeURI="testURI2">test2</subject></subjects><contributors><contributor contributorType="ProjectLeader"><contributorName>Starr, Joan</contributorName><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0002-7285-027X</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0002-7285-1000</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0002-7285-2222</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0002-7285-3333</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0002-7285-4444</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0002-7285-5555</nameIdentifier><affiliation>California Digital Library</affiliation><affiliation>National SPAM Committee</affiliation><affiliation>NASCAR</affiliation></contributor><contributor contributorType="ProjectLeader"><contributorName>Rawls, Lou</contributorName><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0002-7285-027X</nameIdentifier><affiliation>Chicago</affiliation></contributor></contributors><resourceType resourceTypeGeneral="Dataset">Dataset</resourceType><descriptions><description xml:lang="es-419" descriptionType="Abstract">testDescr</description><description xml:lang="zh-Hans" descriptionType="Other">testDescr2</description><description xml:lang="ast" descriptionType="SeriesInformation">testDescr3</description></descriptions></resource>')
    # An item with 2 Creators, both with three nameIDs
    return unicode(
        '<resource xmlns="http://datacite.org/schema/kernel-3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-3 http://schema.datacite.org/meta/kernel-3/metadata.xsd"><identifier identifierType="ARK"/><creators><creator><creatorName>test</creatorName><givenName>Elizabeth</givenName><familyName>Miller</familyName><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/2" nameIdentifierScheme="ORCID2">0000-0001-5000-0002</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/3" nameIdentifierScheme="ORCID3">0000-0001-5000-0003</nameIdentifier><affiliation>DataCite1</affiliation><affiliation>DataCite2</affiliation></creator><creator><creatorName>test</creatorName><givenName>Elizabeth</givenName><familyName>Miller</familyName><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/2" nameIdentifierScheme="ORCID2">0000-0001-5000-0002</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/3" nameIdentifierScheme="ORCID3">0000-0001-5000-0003</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/" nameIdentifierScheme="ORCID">0000-0001-5000-0001</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/2" nameIdentifierScheme="ORCID2">0000-0001-5000-0002</nameIdentifier><nameIdentifier schemeURI="http://orcid.org/3" nameIdentifierScheme="ORCID3">0000-0001-5000-0003</nameIdentifier><affiliation>DataCite1</affiliation><affiliation>DataCite2</affiliation></creator></creators><titles><title xml:lang="en-us">test</title></titles><publisher>test</publisher><publicationYear>1990</publicationYear><subjects><subject xml:lang="ar-afb" schemeURI="testURI" subjectScheme="testScheme">TESTTESTTESTTEST</subject><subject xml:lang="en" subjectScheme="testScheme2" schemeURI="testURI2">test2</subject></subjects><resourceType resourceTypeGeneral="Dataset">Dataset</resourceType><descriptions><description xml:lang="es-419" descriptionType="Abstract">testDescr</description><description xml:lang="zh-Hans" descriptionType="Other">testDescr2</description><description xml:lang="ast" descriptionType="SeriesInformation">testDescr3</description></descriptions></resource>'
    )


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

_elementList = [
    "identifier",
    "creators",
    "creator",
    "creatorName",
    "titles",
    "title",
    "publisher",
    "publicationYear",
    "resourceType",
    "subjects",
    "subject",
    "contributors",
    "contributor",
    "contributorName",
    "givenName",
    "familyName",
    "nameIdentifier",
    "affiliation",
    "affiliationIdentifier",
    "affiliationIdentifierScheme",
    "affiliationIdentifierSchemeURI",
    "dates",
    "date",
    "language",
    "alternateIdentifiers",
    "alternateIdentifier",
    "relatedIdentifiers",
    "relatedIdentifier",
    "sizes",
    "size",
    "formats",
    "format",
    "version",
    "rightsList",
    "rights",
    "descriptions",
    "description",
    "geoLocations",
    "geoLocation",
    "geoLocationPlace",
    "geoLocationPoint",
    "geoLocationBox",
    "geoLocationPolygon",
    "polygonPoint",
    "fundingReferences",
    "fundingReference",
    "funderName",
    "funderIdentifier",
    "awardNumber",
    "awardTitle",
    "pointLongitude",
    "pointLatitude",
    "westBoundLongitude",
    "eastBoundLongitude",
    "southBoundLatitude",
    "northBoundLatitude",
]

_elements = dict((e, i) for i, e in enumerate(_elementList))


def formElementsToDataciteXml(d, shoulder=None, identifier=None):
    """
  The inverse of dataciteXmlToFormElements.  Dictionary entries not
  related to the DataCite metadata schema (Django formset *_FORMS
  entries, etc.) are removed.
  """
    d = {
        k: v
        for (k, v) in d.iteritems()
        if "_FORMS" not in k and any(e in k for e in _elementList)
    }
    d = _addIdentifierInfo(d, shoulder, identifier)
    namespace = "http://datacite.org/schema/kernel-4"
    schemaLocation = "http://schema.datacite.org/meta/kernel-4/metadata.xsd"

    def q(elementName):
        return "{%s}%s" % (namespace, elementName)

    def tagName(tag):
        return tag.split("}")[1]

    root = lxml.etree.Element(q("resource"), nsmap={None: namespace})
    root.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"] = (
        namespace + " " + schemaLocation
    )
    for key, value in d.items():
        value = util.sanitizeXmlSafeCharset(value).strip()
        if value == "":
            continue
        node = root
        while len(key) > 0:
            k, remainder = key.split("-", 1) if "-" in key else (key, "")
            if k in _elements or ("_" in k and k.split("_", 1)[0] in _elements):
                if tagName(node.tag) in _repeatableElementContainers:
                    i, remainder = remainder.split("-", 1)
                    i = int(i)
                    while len(node) <= i:
                        lxml.etree.SubElement(node, q(k))
                    node = node[i]
                    if remainder == k:
                        remainder = ""
                else:
                    n = node.find(q(k))
                    if n != None:
                        node = n
                    else:
                        node = lxml.etree.SubElement(node, q(k))
                    if "_" in k and remainder == k.split("_", 1)[0]:
                        remainder = ""
                if remainder == "":
                    if k == "geoLocationPolygon":
                        parent = node.getparent()
                        parent.insert(
                            parent.index(node) + 1,
                            geometry_util.polygonToDatacite(value)[0],
                        )
                        parent.remove(node)
                    else:
                        node.text = value
            else:
                node.attrib[k] = value
            key = remainder

    def sortValue(node):
        v = tagName(node.tag)
        m = re.match(".*_(\d+)$", v)
        if m:
            return (_elements[v.split("_", 1)[0]], int(m.group(1)))
        else:
            return (_elements[v], 0)

    def sortChildren(node):
        if (
            tagName(node.tag) not in _repeatableElementContainers
            and tagName(node.tag) != "geoLocationPolygon"
        ):
            children = node.getchildren()
            children.sort(key=lambda c: sortValue(c))
            for i, c in enumerate(children):
                node.insert(i, c)
        for c in node.iterchildren():
            sortChildren(c)

    sortChildren(root)
    for tag in _numberedElementContainers:
        for node in root.xpath("//N:" + tag, namespaces={"N": namespace}):
            for t in _numberedElementContainers[tag]:
                for n in node.xpath(
                    "*[substring(local-name(), 1, %d) = '%s']" % (len(t) + 1, t + "_")
                ):
                    n.tag = n.tag.rsplit("_", 1)[0]
    return lxml.etree.tostring(root, encoding=unicode)


def _addIdentifierInfo(d, shoulder=None, identifier=None):
    if shoulder is None:
        assert identifier
        id_str = identifier
    else:
        id_str = shoulder
    d['identifier-identifierType'] = _id_type(id_str)  # Required
    if identifier is not None:
        d['identifier'] = identifier  # Only for already created IDs
    return d


def temp_mockFormElements():
    return {
        u'alternateIdentifiers-alternateIdentifier-0-alternateIdentifier': u'',
        u'alternateIdentifiers-alternateIdentifier-0-alternateIdentifierType': u'',
        u'contributors-contributor-0-affiliation': u'',
        u'contributors-contributor-0-affiliationIdentifier': u'',
        u'contributors-contributor-0-affiliationIdentifierScheme': u'',
        u'contributors-contributor-0-affiliationIdentifierSchemeURI': u'',
        u'contributors-contributor-0-contributorName': u'',
        u'contributors-contributor-0-contributorType': u'',
        u'contributors-contributor-0-familyName': u'',
        u'contributors-contributor-0-givenName': u'',
        u'contributors-contributor-0-nameIdentifier_0-nameIdentifier': u'',
        u'contributors-contributor-0-nameIdentifier_0-nameIdentifierScheme': u'',
        u'contributors-contributor-0-nameIdentifier_0-schemeURI': u'',
        u'contributors-contributor-0-nameIdentifier_1-nameIdentifier': u'',
        u'contributors-contributor-0-nameIdentifier_1-nameIdentifierScheme': u'',
        u'contributors-contributor-0-nameIdentifier_1-schemeURI': u'',
        u'creators-creator-0-affiliation': u'',
        u'creators-creator-0-affiliationIdentifier': u'',
        u'creators-creator-0-affiliationIdentifierScheme': u'',
        u'creators-creator-0-affiliationIdentifierSchemeURI': u'',
        u'creators-creator-0-creatorName': u'test',
        u'creators-creator-0-familyName': u'',
        u'creators-creator-0-givenName': u'',
        u'creators-creator-0-nameIdentifier_0-nameIdentifier': u'',
        u'creators-creator-0-nameIdentifier_0-nameIdentifierScheme': u'',
        u'creators-creator-0-nameIdentifier_0-schemeURI': u'',
        u'creators-creator-0-nameIdentifier_1-nameIdentifier': u'',
        u'creators-creator-0-nameIdentifier_1-nameIdentifierScheme': u'',
        u'creators-creator-0-nameIdentifier_1-schemeURI': u'',
        u'dates-date-0-date': u'',
        u'dates-date-0-dateType': u'',
        u'descriptions-description-0-description': u'',
        u'descriptions-description-0-descriptionType': u'',
        u'descriptions-description-0-{http://www.w3.org/XML/1998/namespace}lang': u'',
        u'formats-format-0-format': u'',
        u'fundingReferences-fundingReference-0-awardNumber': u'',
        u'fundingReferences-fundingReference-0-awardTitle': u'',
        u'fundingReferences-fundingReference-0-awardNumber-awardURI': u'',
        u'fundingReferences-fundingReference-0-funderIdentifier': u'test',
        u'fundingReferences-fundingReference-0-funderIdentifier-funderIdentifierType': u'ISNI',
        u'fundingReferences-fundingReference-0-funderName': u'test',
        u'geoLocations-geoLocation-0-geoLocationBox': u'',
        u'geoLocations-geoLocation-0-geoLocationPlace': u'',
        u'geoLocations-geoLocation-0-geoLocationPoint': u'',
        u'language': u'',
        u'publicationYear': u'1999',
        u'publisher': u'tets',
        u'relatedIdentifiers-relatedIdentifier-0-relatedIdentifier': u'',
        u'relatedIdentifiers-relatedIdentifier-0-relatedIdentifierType': u'',
        u'relatedIdentifiers-relatedIdentifier-0-relatedMetadataScheme': u'',
        u'relatedIdentifiers-relatedIdentifier-0-relationType': u'',
        u'relatedIdentifiers-relatedIdentifier-0-schemeType': u'',
        u'relatedIdentifiers-relatedIdentifier-0-schemeURI': u'',
        u'resourceType': u'Dataset',
        u'resourceType-resourceTypeGeneral': u'Dataset',
        u'rightsList-rights-0-rights': u'',
        u'rightsList-rights-0-rightsURI': u'',
        u'sizes-size-0-size': u'',
        u'subjects-subject-0-schemeURI': u'',
        u'subjects-subject-0-subject': u'',
        u'subjects-subject-0-subjectScheme': u'',
        u'subjects-subject-0-valueURI': u'',
        u'subjects-subject-0-{http://www.w3.org/XML/1998/namespace}lang': u'',
        u'titles-title-0-title': u'test',
        u'titles-title-0-titleType': u'',
        u'titles-title-0-{http://www.w3.org/XML/1998/namespace}lang': u'',
        u'version': u'',
    }
