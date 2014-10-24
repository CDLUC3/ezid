# =============================================================================
#
# EZID :: crossref.py
#
# Interface to CrossRef <http://www.crossref.org/>.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2014, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import lxml.etree
import re
import time
import uuid

import config
import shoulder

_depositorName = None
_depositorEmail = None
_doiTestShoulder = None

def _loadConfig ():
  global _depositorName, _depositorEmail, _doiTestShoulder
  _depositorName = config.config("crossref.depositor_name")
  _depositorEmail = config.config("crossref.depositor_email")
  s = shoulder.getDoiTestShoulder()
  if s != None:
    assert s.key.startswith("doi:")
    _doiTestShoulder = s.key[4:]
  else:
    # Shoulder never happen.
    _doiTestShoulder = "10.????"

_loadConfig()
config.addLoader(_loadConfig)

_prologRE = re.compile("<\?xml\s+version\s*=\s*['\"]([-\w.:]+)[\"']" +\
  "(\s+encoding\s*=\s*['\"]([-\w.]+)[\"'])?" +\
  "(\s+standalone\s*=\s*['\"](yes|no)[\"'])?\s*\?>\s*")
_utf8RE = re.compile("UTF-?8$", re.I)
_schemaLocation = "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"
_schemaLocationTemplate =\
  "http://www.crossref.org/schema/deposit/crossref%s.xsd"
_tagRE =\
  re.compile("\{(http://www\.crossref\.org/schema/(4\.3\.\d))\}([-\w.]+)$")
_rootTags = ["journal", "book", "conference", "sa_component", "dissertation",
  "report-paper", "standard", "database"]
_crossrefTestPrefix = "10.9876/"

def _notOne (n):
  if n == 0:
    return "no"
  else:
    return "more than one"

def _addDeclaration (document):
  # We don't use lxml's xml_declaration argument because it doesn't
  # allow us to add a basic declaration without also adding an
  # encoding declaration, which we don't want.
  return "<?xml version=\"1.0\"?>\n" + document

def validateBody (body):
  """
  Validates and normalizes an immediate child element of a <body>
  element of a CrossRef metadata submission document.  'body' should
  be a Unicode string.  Either a normalized XML document is returned
  or an assertion error is raised.  Validation is limited to checking
  that 'body' is well-formed XML, that it appears to be a <body> child
  element, and that the elements that EZID cares about are present and
  well-formed.  Normalization includes stripping off any <doi_batch>
  or <body> elements enclosing the child element, and normalizing the
  one and only <doi_data> element.
  """
  # Strip off any prolog.
  m = _prologRE.match(body)
  if m:
    assert m.group(1) == "1.0", "unsupported XML version"
    if m.group(2) != None:
      assert _utf8RE.match(m.group(3)), "XML encoding must be UTF-8"
    if m.group(4) != None:
      assert m.group(5) == "yes", "XML document must be standalone"
    body = body[len(m.group(0)):]
  # Parse the document.
  try:
    root = lxml.etree.XML(body)
  except Exception, e:
    assert False, "XML parse error: " + str(e)
  m = _tagRE.match(root.tag)
  assert m is not None, "not CrossRef submission metadata"
  namespace = m.group(1)
  version = m.group(2)
  ns = { "N": namespace }
  # Locate the <body> child element.
  if m.group(3) == "doi_batch":
    root = root.find("N:body", namespaces=ns)
    assert root is not None, "malformed CrossRef submission metadata"
    m = _tagRE.match(root.tag)
  if m.group(3) == "body":
    assert len(list(root)) == 1, "malformed CrossRef submission metadata"
    root = root[0]
    m = _tagRE.match(root.tag)
    assert m is not None, "malformed CrossRef submission metadata"
  assert m.group(3) in _rootTags,\
    "XML document root is not a CrossRef <body> child element"
  # Locate and normalize the one and only <doi_data> element.
  doiData = root.xpath("//N:doi_data", namespaces=ns)
  assert len(doiData) == 1, "XML document contains %s <doi_data> element" %\
    _notOne(len(doiData))
  doiData = doiData[0]
  doi = doiData.findall("N:doi", namespaces=ns)
  assert len(doi) == 1,\
    "<doi_data> element contains %s <doi> subelement" % _notOne(len(doi))
  doi = doi[0]
  doi.text = "(:tba)"
  resource = doiData.findall("N:resource", namespaces=ns)
  assert len(resource) == 1,\
    "<doi_data> element contains %s <resource> subelement" %\
    _notOne(len(resource))
  resource = resource[0]
  resource.text = "(:tba)"
  assert doiData.find("N:collection", namespaces=ns) == None,\
    "<doi_data> element contains disallowed <collection> subelement"
  e = doiData.find("N:timestamp", namespaces=ns)
  if e != None: doiData.remove(e)
  assert doiData.find("N:timestamp", namespaces=ns) == None,\
    "<doi_data> element contains more than one <timestamp> subelement"
  # Normalize schema declarations.
  root.attrib[_schemaLocation] =\
    namespace + " " + (_schemaLocationTemplate % version)
  try:
    return _addDeclaration(lxml.etree.tostring(root, encoding="unicode"))
  except Exception, e:
    assert False, "XML serialization error: " + str(e)

def _buildDeposit (body, registrant, doi, targetUrl):
  """
  Builds a CrossRef metadata submission document.  'body' should be a
  CrossRef <body> child element as a Unicode string, and is assumed to
  have been validated and normalized per validateBody above.
  'registrant' is inserted in the header.  'doi' should be a
  scheme-less DOI identifier (e.g., "10.5060/FOO").  The return is a
  tuple (document, body, batchId) where 'document' is the entire
  submission document as a serialized Unicode string (with the DOI and
  target URL inserted), 'body' is the same but just the <body> child
  element, and 'batchId' is the submission batch identifier.  If 'doi'
  is a test identifier, it is prefixed with _crossrefTestPrefix in
  'document' only.
  """
  body = lxml.etree.XML(body)
  m = _tagRE.match(body.tag)
  namespace = m.group(1)
  version = m.group(2)
  ns = { "N": namespace }
  doiData = body.xpath("//N:doi_data", namespaces=ns)[0]
  doiElement = doiData.find("N:doi", namespaces=ns)
  doiElement.text = doi
  doiData.find("N:resource", namespaces=ns).text = targetUrl
  d1 = _addDeclaration(lxml.etree.tostring(body, encoding="unicode"))
  def q (elementName):
    return "{%s}%s" % (namespace, elementName)
  root = lxml.etree.Element(q("doi_batch"), version=version)
  root.attrib[_schemaLocation] = body.attrib[_schemaLocation]
  head = lxml.etree.SubElement(root, q("head"))
  batchId = str(uuid.uuid1())
  lxml.etree.SubElement(head, q("doi_batch_id")).text = batchId
  lxml.etree.SubElement(head, q("timestamp")).text = str(int(time.time()*100))
  e = lxml.etree.SubElement(head, q("depositor"))
  if version >= "4.3.4":
    lxml.etree.SubElement(e, q("depositor_name")).text = _depositorName
  else:
    lxml.etree.SubElement(e, q("name")).text = _depositorName
  lxml.etree.SubElement(e, q("email_address")).text = _depositorEmail
  lxml.etree.SubElement(head, q("registrant")).text = registrant
  e = lxml.etree.SubElement(root, q("body"))
  del body.attrib[_schemaLocation]
  if doi.startswith(_doiTestShoulder):
    doiElement.text = _crossrefTestPrefix + doi
  e.append(body)
  d2 = _addDeclaration(lxml.etree.tostring(root, encoding="unicode"))
  return (d1, d2, batchId)

def _multipartBody (*parts):
  """
  Builds a multipart/form-data (RFC 2388) document out of a list of
  constituent parts.  Each part is either a 2-tuple (name, value) or a
  4-tuple (name, filename, contentType, value).  Returns a tuple
  (document, boundary).
  """
  while True:
    boundary = "BOUNDARY_%s" % uuid.uuid1().hex
    collision = False
    for p in parts:
      for e in p:
        if boundary in e: collision = True
    if not collision: break
  body = []
  for p in parts:
    body.append("--" + boundary)
    if len(p) == 2:
      body.append("Content-Disposition: form-data; name=\"%s\"" % p[0])
      body.append("")
      body.append(p[1])
    else:
      body.append(("Content-Disposition: form-data; name=\"%s\"; " +\
        "filename=\"%s\"") % (p[0], p[1]))
      body.append("Content-Type: " + p[2])
      body.append("")
      body.append(p[3])
  body.append("--%s--" % boundary)
  return ("\r\n".join(body), boundary)
