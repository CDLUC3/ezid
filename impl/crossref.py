#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import re
import time
import uuid

import django.conf
import lxml
import lxml.etree

import impl.util

ROOT_TAGS = [
    "journal",
    "book",
    "conference",
    "sa_component",
    "dissertation",
    "report-paper",
    "standard",
    "database",
    "peer_review",
    "posted_content",
]

TITLE_PATH_LIST = [
    "../N:titles/N:title",
    "../N:titles/N:original_language_title",
    "../N:proceedings_title",
    "../N:full_title",
    "../N:abbrev_title",
]

PROLOG_RX = re.compile(
    "<\\?xml\\s+version\\s*=\\s*['\"]([-\\w.:]+)[\"']"
    + "(\\s+encoding\\s*=\\s*['\"]([-\\w.]+)[\"'])?"
    + "(\\s+standalone\\s*=\\s*['\"](yes|no)[\"'])?\\s*\\?>\\s*"
)
UTF8_RX = re.compile("UTF-?8$", re.I)
SCHEMA_LOCATION_STR = "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"
SCHEMA_LOCATION_FORMAT_STR = "http://www.crossref.org/schema/deposit/crossref{}.xsd"

ROOT_TAG_LIST = [
    "journal",
    "book",
    "conference",
    "sa_component",
    "dissertation",
    "report-paper",
    "standard",
    "database",
]

# noinspection HttpUrlsUsage
TAG_REGEX = re.compile("{(http://www\\.crossref\\.org/schema/(4\.[34]\.\d|5\.[34]\.\d))}([-\\w.]+)$")

def _notOne (n):
  if n == 0:
    return "no"
  else:
    return "more than one"

# noinspection PyUnresolvedReferences
def validateBody(body):
    """Validate and normalize an immediate child element of a <body> element of
    a Crossref metadata submission document

    'body' should be a Unicode string. Either a normalized XML document
    is returned or an assertion error is raised. Validation is limited to
    checking that 'body' is well-formed XML, that it appears to be a
    <body> child element, and that the elements that EZID cares about are
    present and well-formed. Normalization includes stripping off any
    <doi_batch> or <body> elements enclosing the child element, and
    normalizing the one and only <doi_data> element.
    """
    # Strip off any prolog.
    m = PROLOG_RX.match(body)
    if m:
        assert m.group(1) == "1.0", "unsupported XML version"
        if m.group(2) is not None:
            assert UTF8_RX.match(m.group(3)), "XML encoding must be utf-8"
        if m.group(4) is not None:
            assert m.group(5) == "yes", "XML document must be standalone"
        body = body[len(m.group(0)) :]
    # Parse the document.
    try:
        root = lxml.etree.XML(body)
    except Exception as e:
        assert False, "XML parse error: " + str(e)
    m = TAG_REGEX.match(root.tag)
    assert m is not None, "not Crossref submission metadata"
    namespace = m.group(1)
    version = m.group(2)
    ns = {"N": namespace}
    # Locate the <body> child element.
    if m.group(3) == "doi_batch":
        root = root.find("N:body", namespaces=ns)
        assert root is not None, "malformed Crossref submission metadata"
        m = TAG_REGEX.match(root.tag)
    if m.group(3) == "body":
        assert len(list(root)) == 1, "malformed Crossref submission metadata"
        root = root[0]
        m = TAG_REGEX.match(root.tag)
        assert m is not None, "malformed Crossref submission metadata"
    assert m.group(3) in ROOT_TAGS, "XML document root is not a Crossref <body> child element"
    # Locate and normalize the one and only <doi_data> element.
    doiData = root.xpath("//N:doi_data", namespaces=ns)
    assert len(doiData) == 1, "XML document contains {} <doi_data> element".format(
        _notOne(len(doiData))
    )
    doiData = doiData[0]
    doi = doiData.findall("N:doi", namespaces=ns)
    assert len(doi) == 1, "<doi_data> element contains {} <doi> subelement".format(
        _notOne(len(doi))
    )
    doi = doi[0]
    doi.text = "(:tba)"
    resource = doiData.findall("N:resource", namespaces=ns)
    assert (
        len(resource) == 1
    ), f"<doi_data> element contains {_notOne(len(resource))} <resource> subelement"
    resource = resource[0]
    resource.text = "(:tba)"
    assert (
        doiData.find("N:collection/N:item/N:doi", namespaces=ns) is None
    ), "<doi_data> element contains more than one <doi> subelement"
    e = doiData.find("N:timestamp", namespaces=ns)
    if e is not None:
        doiData.remove(e)
    assert (
        doiData.find("N:timestamp", namespaces=ns) is None
    ), "<doi_data> element contains more than one <timestamp> subelement"
    # Normalize schema declarations.
    root.attrib[SCHEMA_LOCATION_STR] = namespace + " " + (SCHEMA_LOCATION_FORMAT_STR.format(version))
    try:
        # We re-sanitize the document because unacceptable characters can
        # be (and have been) introduced via XML character entities.
        return _addDeclaration(
            impl.util.sanitizeXmlSafeCharset(lxml.etree.tostring(root, encoding="unicode"))
        )
    except Exception as e:
        assert False, "XML serialization error: " + str(e)


# In the Crossref deposit schema, version 4.3.4, the <doi_data>
# element can occur in 20 different places. An analysis shows that
# the resource title corresponding to the DOI being defined can be
# found by one or more of the following XPaths relative to the
# <doi_data> element.


def replaceTbas(body, doi, targetUrl):
    """Fill in the (:tba) portions of Crossref deposit metadata with the given
    arguments

    'body' should be a Crossref <body> child element as a Unicode string,
    and is assumed to have been validated and normalized per validateBody
    above. 'doi' should be a scheme-less DOI identifier (e.g.,
    "10.5060/FOO"). The return is a Unicode string.
    """
    return _buildDeposit(body, None, doi, targetUrl, bodyOnly=True)


def _buildDeposit(body, registrant, doi, targetUrl, withdrawTitles=False, bodyOnly=False):
    """Build a Crossref metadata submission document

    'body' should be a
    Crossref <body> child element as a Unicode string, and is assumed to
    have been validated and normalized per validateBody above.
    'registrant' is inserted in the header. 'doi' should be a
    scheme-less DOI identifier (e.g., "10.5060/FOO"). The return is a
    tuple (document, body, batchId) where 'document' is the entire
    submission document as a serialized Unicode string (with the DOI and
    target URL inserted), 'body' is the same but just the <body> child
    element, and 'batchId' is the submission batch identifier.
    Options: if 'withdrawTitles' is true, the title(s) corresponding to
    the DOI being defined are prepended with "WITHDRAWN:" (in 'document'
    only). If 'bodyOnly' is true, only the body is returned.
    """
    body = lxml.etree.XML(body)
    m = TAG_REGEX.match(body.tag)
    namespace = m.group(1)
    version = m.group(2)
    ns = {"N": namespace}
    doiData = body.xpath("//N:doi_data", namespaces=ns)[0]
    doiElement = doiData.find("N:doi", namespaces=ns)
    doiElement.text = doi
    doiData.find("N:resource", namespaces=ns).text = targetUrl
    d1 = _addDeclaration(lxml.etree.tostring(body, encoding="unicode"))
    if bodyOnly:
        return d1

    def q(elementName):
        return f"{{{namespace}}}{elementName}"

    root = lxml.etree.Element(q("doi_batch"), version=version)
    root.attrib[SCHEMA_LOCATION_STR] = body.attrib[SCHEMA_LOCATION_STR]

    # TODO: This section is also in proc-crossref.py
    # START
    head = lxml.etree.SubElement(root, q("head"))
    batchId = str(uuid.uuid1())
    lxml.etree.SubElement(head, q("doi_batch_id")).text = batchId
    lxml.etree.SubElement(head, q("timestamp")).text = str(int(time.time() * 100))
    e = lxml.etree.SubElement(head, q("depositor"))
    if version >= "4.3.4":
        lxml.etree.SubElement(
            e, q("depositor_name")
        ).text = django.conf.settings.CROSSREF_DEPOSITOR_NAME
    else:
        lxml.etree.SubElement(e, q("name")).text = django.conf.settings.CROSSREF_DEPOSITOR_NAME
    lxml.etree.SubElement(
        e, q("email_address")
    ).text = django.conf.settings.CROSSREF_DEPOSITOR_EMAIL
    lxml.etree.SubElement(head, q("registrant")).text = registrant
    e = lxml.etree.SubElement(root, q("body"))
    # END

    del body.attrib[SCHEMA_LOCATION_STR]
    if withdrawTitles:
        for p in TITLE_PATH_LIST:
            for t in doiData.xpath(p, namespaces=ns):
                if t.text is not None:
                    t.text = "WITHDRAWN: " + t.text
    e.append(body)
    d2 = _addDeclaration(lxml.etree.tostring(root, encoding="unicode"))
    return d2, d1, batchId


def _addDeclaration(document):
    # We don't use lxml's xml_declaration argument because it doesn't
    # allow us to add a basic declaration without also adding an
    # encoding declaration, which we don't want.
    return '<?xml version="1.0"?>\n' + document
