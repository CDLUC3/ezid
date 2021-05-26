import impl.util
import lxml.etree
import lxml
import impl.datacite

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


_titlePaths = [
    "../N:titles/N:title",
    "../N:titles/N:original_language_title",
    "../N:proceedings_title",
    "../N:full_title",
    "../N:abbrev_title",
]


# noinspection PyUnresolvedReferences
def validateBody(body):
    """Validates and normalizes an immediate child element of a <body> element of
    a Crossref metadata submission document.

    'body' should be a Unicode string.  Either a normalized XML document
    is returned or an assertion error is raised.  Validation is limited to
    checking that 'body' is well-formed XML, that it appears to be a
    <body> child element, and that the elements that EZID cares about are
    present and well-formed.  Normalization includes stripping off any
    <doi_batch> or <body> elements enclosing the child element, and
    normalizing the one and only <doi_data> element.
    """
    # Strip off any prolog.
    m = impl.datacite._prologRE.match(body)
    if m:
        assert m.group(1) == "1.0", "unsupported XML version"
        if m.group(2) is not None:
            assert impl.datacite._utf8RE.match(m.group(3)), "XML encoding must be utf-8"
        if m.group(4) is not None:
            assert m.group(5) == "yes", "XML document must be standalone"
        body = body[len(m.group(0)):]
    # Parse the document.
    try:
        root = lxml.etree.XML(body)
    except Exception as e:
        assert False, "XML parse error: " + str(e)
    m = impl.datacite._tagRE.match(root.tag)
    assert m is not None, "not Crossref submission metadata"
    namespace = m.group(1)
    version = m.group(2)
    ns = {"N": namespace}
    # Locate the <body> child element.
    if m.group(3) == "doi_batch":
        root = root.find("N:body", namespaces=ns)
        assert root is not None, "malformed Crossref submission metadata"
        m = impl.datacite._tagRE.match(root.tag)
    if m.group(3) == "body":
        assert len(list(root)) == 1, "malformed Crossref submission metadata"
        root = root[0]
        m = impl.datacite._tagRE.match(root.tag)
        assert m is not None, "malformed Crossref submission metadata"
    assert (
        m.group(3) in ROOT_TAGS
    ), "XML document root is not a Crossref <body> child element"
    # Locate and normalize the one and only <doi_data> element.
    doiData = root.xpath("//N:doi_data", namespaces=ns)
    assert len(doiData) == 1, "XML document contains {} <doi_data> element".format(
        impl.datacite._notOne(len(doiData))
    )
    doiData = doiData[0]
    doi = doiData.findall("N:doi", namespaces=ns)
    assert len(doi) == 1, "<doi_data> element contains {} <doi> subelement".format(
        impl.datacite._notOne(len(doi))
    )
    doi = doi[0]
    doi.text = "(:tba)"
    resource = doiData.findall("N:resource", namespaces=ns)
    assert (
        len(resource) == 1
    ), f"<doi_data> element contains {impl.datacite._notOne(len(resource))} <resource> subelement"
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
    root.attrib[impl.datacite._schemaLocation] = (
        namespace + " " + (impl.datacite._schemaLocationTemplate.format(version))
    )
    try:
        # We re-sanitize the document because unacceptable characters can
        # be (and have been) introduced via XML character entities.
        return impl.datacite._addDeclaration(
            impl.util.sanitizeXmlSafeCharset(
                lxml.etree.tostring(root, encoding="unicode")
            )
        )
    except Exception as e:
        assert False, "XML serialization error: " + str(e)

# In the Crossref deposit schema, version 4.3.4, the <doi_data>
# element can occur in 20 different places.  An analysis shows that
# the resource title corresponding to the DOI being defined can be
# found by one or more of the following XPaths relative to the
# <doi_data> element.


def replaceTbas(body, doi, targetUrl):
    """Fills in the (:tba) portions of Crossref deposit metadata with the given
    arguments.

    'body' should be a Crossref <body> child element as a Unicode string,
    and is assumed to have been validated and normalized per validateBody
    above.  'doi' should be a scheme-less DOI identifier (e.g.,
    "10.5060/FOO").  The return is a Unicode string.
    """
    return impl.datacite._buildDeposit(body, None, doi, targetUrl, bodyOnly=True)
