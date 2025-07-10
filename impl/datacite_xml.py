#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Allows processing a form with form elements named with simple XPATH
expressions

1) Generates form fields for use with Django form model.
2) Creates an XML document for attaching Datacite XML metadata.
"""

import collections
import re

import lxml.etree

import impl.datacite
import impl.geometry_util
import impl.util

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
    "relatedItems"
]

_numberedElementContainers = {
    "creator": ["nameIdentifier"],
    "contributor": ["nameIdentifier"],
}

_maxNumberedElements = 2


def dataciteXmlToFormElements(document):
    """Convert a DataCite XML record to a dictionary of form elements. All
    non-content (comments, etc.) is discarded. Whitespace is processed and
    empty element and attribute values are discarded. Dictionary keys follow
    the pattern of element and attribute XPaths, e.g., the schemeURI attribute
    in the following XML fragment:

      <resource>
        <creators>
          <creator>...</creator>
          <creator>
            <nameIdentifier schemeURI="...">

    is identified by key:

      creators-creator-1-nameIdentifier_0-schemeURI

    Repeatable elements are indexed at the top level only; lower-level
    repeatable elements (e.g., contributor affiliations) are
    concatenated. However, certain repeatable elements (see
    _numberedElementContainers), such as nameIdentifier in the example
    above, are indexed, but with underscores. An additional tweak to
    the naming pattern is that the key for the content of a top-level
    repeatable element carries an extra component that echoes the
    element name, as in:

      alternateIdentifiers-alternateIdentifier-0-alternateIdentifier
      alternateIdentifiers-alternateIdentifier-1-alternateIdentifier

    <br> elements in descriptions are replaced with newlines.
    """
    document = impl.datacite.upgradeDcmsRecord_v2(document)
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
            mypath = f"{path}-{tag}"
        if index is not None:
            mypath += f"{separator}{index:d}"
            mypathx = f"{mypath}-{tag}"
        else:
            mypathx = mypath
        for a in node.attrib:
            v = node.attrib[a].strip()
            if v != "":
                d[f"{mypath}-{a}"] = v
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
                    if isinstance(c.tag, str) and tagName(c.tag) == "br":
                        v += "\n"
                    v += c.tail or ""
                v = v.strip()
                if v != "":
                    d[mypathx] = v
            elif tag == "geoLocationPolygon":
                d[mypathx] = impl.geometry_util.datacitePolygonToInternal(node)
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

    root = impl.util.parseXmlString(document)
    for c in getElementChildren(root):
        processNode("", c)
    fc = _separateByFormType(d)
    return fc

""" Representation of django forms and formsets used for DataCite XML """
FormColl = collections.namedtuple(
    'FormColl',
    'nonRepeating publisher resourceType creators titles descrs subjects contribs dates altids relids sizes formats rights geoLocations fundingReferences relatedItems',
)

def _separateByFormType(d):
    """Organize form elements into a manageable collection Turn empty dicts
    into None so that forms render properly

    Nonrepeating fields (fields that can't be repeated into multiple
    forms) are:    identifier, identifier-identifierType, language,
    publisher, publicationYear, version
    """
    _nonRepeating = {
        k: v
        for (k, v) in list(d.items())
        if not any(e in k for e in _repeatableElementContainers)
        and not k.startswith('resourceType')
    }

    def dict_generate(d, s):
        dr = {k: v for (k, v) in list(d.items()) if k.startswith(s)}
        return dr if dr else None

    return FormColl(
        nonRepeating=_nonRepeating if _nonRepeating else None,
        publisher=dict_generate(d, 'publisher'),
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
        relatedItems=dict_generate(d, 'relatedItems')
    )


def _id_type(str):
    m = re.compile("^[a-z]+")
    if m.search(str) is None:
        return ''
    else:
        return m.findall(str)[0].upper()


# The following exhaustive list of DataCite XML elements must form a
# partial topological order, that is, if two elements have the same
# parent, they must appear in the list in the same order that they
# must appear in an XML document defined in datacite/metadata.xsd.
# Embedded elements such as the titles, creators and contributors in 
# the relatedItems may have a different topological order than what 
# they appear at the element level. Define the order in a sub-elements 
# list when needed.

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
    "pointLongitude",
    "pointLatitude",
    "westBoundLongitude",
    "eastBoundLongitude",
    "southBoundLatitude",
    "northBoundLatitude",
    "fundingReferences",
    "fundingReference",
    "funderName",
    "funderIdentifier",
    "awardNumber",
    "awardTitle",
    "relatedItems",
    "relatedItem",
    "relatedItemIdentifier",
    "volume",
    "issue",
    "number",
    "firstPage",
    "lastPage",
    "edition",
]

_elementList_relatedItem = [
    "relatedItemIdentifier",
    "creators",
    "creator",
    "creatorName",
    "titles",
    "title",
    "publicationYear",
    "volume",
    "issue",
    "number",
    "firstPage",
    "lastPage",
    "publisher",
    "edition",
    "contributors",
    "contributor",
    "givenName",
    "familyName",
]

# elements with topological order in sequence number, such as:
# {'identifier': 0, 'creators': 1, 'creator': 2, 'creatorName': 3, etc.
_elements = dict((e, i) for i, e in enumerate(_elementList))

_elements_relatedItem = dict((e, i) for i, e in enumerate(_elementList_relatedItem))


def formElementsToDataciteXml(d, shoulder=None, identifier=None):
    """The inverse of dataciteXmlToFormElements

    Dictionary entries not related to the DataCite metadata schema
    (Django formset *_FORMS entries, etc.) are removed.
    """
    d = {
        k: v
        for (k, v) in list(d.items())
        if "_FORMS" not in k and any(e in k for e in _elementList)
    }
    d = _addIdentifierInfo(d, shoulder, identifier)
    namespace = "http://datacite.org/schema/kernel-4"
    schemaLocation = "http://schema.datacite.org/meta/kernel-4/metadata.xsd"

    def q(elementName):
        return f"{{{namespace}}}{elementName}"

    def tagName(tag):
        return tag.split("}")[1]

    root = lxml.etree.Element(q("resource"), nsmap={None: namespace})
    root.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"] = (
        namespace + " " + schemaLocation
    )
    for key, value in list(d.items()):
        value = impl.util.sanitizeXmlSafeCharset(value).strip()
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
                    if n is not None:
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
                            impl.geometry_util.polygonToDatacite(value)[0],
                        )
                        parent.remove(node)
                    else:
                        node.text = value
            else:
                node.attrib[k] = value
            key = remainder

    def sortValue(node, ordered_elements):
        v = tagName(node.tag)
        m = re.match(".*_(\\d+)$", v)
        if m:
            return ordered_elements[v.split("_", 1)[0]], int(m.group(1))
        else:
            return ordered_elements[v], 0

    def sortChildren(node):
        if (
            tagName(node.tag) not in _repeatableElementContainers
            and tagName(node.tag) != "geoLocationPolygon"
        ):
            if tagName(node.tag) == "relatedItem":
                ordered_elements = _elements_relatedItem
            else:
                ordered_elements = _elements
            children = node.getchildren()
            children.sort(key=lambda c: sortValue(c, ordered_elements))
            for i, c in enumerate(children):
                node.insert(i, c)
        for c in node.iterchildren():
            sortChildren(c)

    sortChildren(root)
    for tag in _numberedElementContainers:
        for node in root.xpath("//N:" + tag, namespaces={"N": namespace}):
            for t in _numberedElementContainers[tag]:
                for n in node.xpath(
                    f"*[substring(local-name(), 1, {len(t) + 1:d}) = '{t + '_'}']"
                ):
                    n.tag = n.tag.rsplit("_", 1)[0]
    return lxml.etree.tostring(root, encoding=str)


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
        'alternateIdentifiers-alternateIdentifier-0-alternateIdentifier': '',
        'alternateIdentifiers-alternateIdentifier-0-alternateIdentifierType': '',
        'contributors-contributor-0-affiliation': '',
        'contributors-contributor-0-affiliationIdentifier': '',
        'contributors-contributor-0-affiliationIdentifierScheme': '',
        'contributors-contributor-0-schemeURI': '',
        'contributors-contributor-0-contributorName': '',
        'contributors-contributor-0-contributorType': '',
        'contributors-contributor-0-familyName': '',
        'contributors-contributor-0-givenName': '',
        'contributors-contributor-0-nameIdentifier_0-nameIdentifier': '',
        'contributors-contributor-0-nameIdentifier_0-nameIdentifierScheme': '',
        'contributors-contributor-0-nameIdentifier_0-schemeURI': '',
        'contributors-contributor-0-nameIdentifier_1-nameIdentifier': '',
        'contributors-contributor-0-nameIdentifier_1-nameIdentifierScheme': '',
        'contributors-contributor-0-nameIdentifier_1-schemeURI': '',
        'creators-creator-0-affiliation': '',
        'creators-creator-0-affiliationIdentifier': '',
        'creators-creator-0-affiliationIdentifierScheme': '',
        'creators-creator-0-schemeURI': '',
        'creators-creator-0-creatorName': 'test',
        'creators-creator-0-familyName': '',
        'creators-creator-0-givenName': '',
        'creators-creator-0-nameIdentifier_0-nameIdentifier': '',
        'creators-creator-0-nameIdentifier_0-nameIdentifierScheme': '',
        'creators-creator-0-nameIdentifier_0-schemeURI': '',
        'creators-creator-0-nameIdentifier_1-nameIdentifier': '',
        'creators-creator-0-nameIdentifier_1-nameIdentifierScheme': '',
        'creators-creator-0-nameIdentifier_1-schemeURI': '',
        'dates-date-0-date': '',
        'dates-date-0-dateType': '',
        'dates-date-0-dateInformation': '',
        'descriptions-description-0-description': '',
        'descriptions-description-0-descriptionType': '',
        'descriptions-description-0-{http://www.w3.org/XML/1998/namespace}lang': '',
        'formats-format-0-format': '',
        'fundingReferences-fundingReference-0-awardNumber': '',
        'fundingReferences-fundingReference-0-awardTitle': '',
        'fundingReferences-fundingReference-0-awardNumber-awardURI': '',
        'fundingReferences-fundingReference-0-funderIdentifier': 'test',
        'fundingReferences-fundingReference-0-funderIdentifier-funderIdentifierType': 'ISNI',
        'fundingReferences-fundingReference-0-funderName': 'test',
        'geoLocations-geoLocation-0-geoLocationBox': '',
        'geoLocations-geoLocation-0-geoLocationPlace': '',
        'geoLocations-geoLocation-0-geoLocationPoint': '',
        'language': '',
        'publicationYear': '1999',
        'publisher': 'test',
        'relatedIdentifiers-relatedIdentifier-0-relatedIdentifier': '',
        'relatedIdentifiers-relatedIdentifier-0-relatedIdentifierType': '',
        'relatedIdentifiers-relatedIdentifier-0-relatedMetadataScheme': '',
        'relatedIdentifiers-relatedIdentifier-0-relationType': '',
        'relatedIdentifiers-relatedIdentifier-0-schemeType': '',
        'relatedIdentifiers-relatedIdentifier-0-schemeURI': '',
        'resourceType': 'Dataset',
        'resourceType-resourceTypeGeneral': 'Dataset',
        'rightsList-rights-0-rights': '',
        'rightsList-rights-0-rightsURI': '',
        'sizes-size-0-size': '',
        'subjects-subject-0-schemeURI': '',
        'subjects-subject-0-subject': '',
        'subjects-subject-0-subjectScheme': '',
        'subjects-subject-0-valueURI': '',
        'subjects-subject-0-{http://www.w3.org/XML/1998/namespace}lang': '',
        'titles-title-0-title': 'test',
        'titles-title-0-titleType': '',
        'titles-title-0-{http://www.w3.org/XML/1998/namespace}lang': '',
        'version': '',
    }
