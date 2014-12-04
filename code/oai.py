# =============================================================================
#
# EZID :: oai.py
#
# Support for OAI-PMH 2.0
# <http://www.openarchives.org/OAI/openarchivesprotocol.html>.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2014, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.http
import lxml.etree
import threading
import time
import urllib

import config
import mapping
import shoulder
import store

_enabled = None
_baseUrl = None
_repositoryName = None
_adminEmail = None
_lock = threading.Lock()
_testShoulders = None

def _loadConfig ():
  global _enabled, _baseUrl, _repositoryName, _adminEmail, _testShoulders
  _enabled = (config.config("oai.enabled").lower() == "true")
  _baseUrl = config.config("DEFAULT.ezid_base_url")
  _repositoryName = config.config("oai.repository_name")
  _adminEmail = config.config("oai.admin_email")
  _lock.acquire()
  _testShoulders = None
  _lock.release()

_loadConfig()
config.addLoader(_loadConfig)

def _getTestShoulders ():
  global _testShoulders
  _lock.acquire()
  try:
    if _testShoulders is None:
      _testShoulders = []
      s = shoulder.getArkTestShoulder()
      if s is not None: _testShoulders.append(s.key)
      s = shoulder.getDoiTestShoulder()
      if s is not None: _testShoulders.append(s.key)
    return _testShoulders
  finally:
    _lock.release()

def _defaultTarget (identifier):
  return "%s/id/%s" % (_baseUrl, urllib.quote(identifier, ":/"))

def isVisible (identifier, metadata):
  """
  Returns true if 'identifier' is (should be) visible in the OAI-PMH
  feed.  'identifier' should be a qualified, normalized identifier,
  e.g., "doi:10.5060/FOO".  'metadata' should be the identifier's
  metadata as a dictionary.
  """
  if any(identifier.startswith(s) for s in _getTestShoulders()): return False
  # Well, isn't this subtle and ugly: this function gets called by the
  # 'store' module, in which case the metadata dictionary contains
  # noid commands to *change* metadata values, not the final stored
  # values.  Ergo, we have to check for empty values.
  status = metadata.get("_is", "public")
  if status == "": status = "public"
  if status != "public": return False
  export = metadata.get("_x", "yes")
  if export == "": export = "yes"
  if export != "yes": return False
  if metadata.get("_st", metadata["_t"]) == _defaultTarget(identifier):
    return False
  m = mapping.getDisplayMetadata(metadata)
  if m[0] is None or m[1] is None or m[3] is None: return False
  return True

def _q (elementName):
  return "{http://www.openarchives.org/OAI/2.0/}" + elementName

def _formatTime (t):
  return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))

def _buildResponse (oaiRequest, body):
  root = lxml.etree.Element(_q("OAI-PMH"),
    nsmap={ None: "http://www.openarchives.org/OAI/2.0/" })
  root.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"] =\
    "http://www.openarchives.org/OAI/2.0/ " +\
    "http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd"
  root.addprevious(lxml.etree.ProcessingInstruction("xml-stylesheet",
    "type='text/xsl' href='/static/stylesheets/oai2.xsl'"))
  lxml.etree.SubElement(root, _q("responseDate")).text =\
    _formatTime(int(time.time()))
  e = lxml.etree.SubElement(root, _q("request"))
  e.text = _baseUrl + "/oai"
  if not body.tag.endswith("}error") or\
    body.attrib["code"] not in ["badVerb", "badArgument"]:
    e.attrib["verb"] = oaiRequest[0]
    for k, v in oaiRequest[1].items(): e.attrib[k] = v
  root.append(body)
  return lxml.etree.tostring(root.getroottree(), encoding="UTF-8",
    xml_declaration=True)

def _error (oaiRequest, code, message=None):
  e = lxml.etree.Element(_q("error"))
  e.attrib["code"] = code
  if message != None: e.text = message
  return _buildResponse(oaiRequest, e)

_arguments = {
  # verb: { argument: R (required), O (optional), X (exclusive) }
  "GetRecord": {
    "identifier": "R",
    "metadataPrefix": "R" },
  "Identify": {},
  "ListIdentifiers": {
    "metadataPrefix": "R",
    "from": "O",
    "until": "O",
    "set": "O",
    "resumptionToken": "X" },
  "ListMetadataFormats": {
    "identifier": "O" },
  "ListRecords": {
    "metadataPrefix": "R",
    "from": "O",
    "until": "O",
    "set": "O",
    "resumptionToken": "X" },
  "ListSets": {
    "resumptionToken": "X" }
}

def _buildRequest (request):
  if len(request.REQUEST.getlist("verb")) != 1: return _error(None, "badVerb")
  verb = request.REQUEST["verb"]
  if verb not in _arguments: return _error(None, "badVerb")
  r = (verb, {})
  exclusive = False
  for k in request.REQUEST:
    if k == "verb": continue
    if len(request.REQUEST.getlist(k)) > 1: return _error(None, "badArgument")
    if k not in _arguments[verb]: return _error(None, "badArgument")
    if _arguments[verb][k] == "X":
      if len(request.REQUEST.keys()) > 2: return _error(None, "badArgument")
      exclusive = True
    r[1][k] = request.REQUEST[k]
  if not exclusive:
    for k, rox in _arguments[verb].items():
      if rox == "R" and k not in r[1]: return _error(None, "badArgument")
  return r

def _doIdentify (oaiRequest):
  e = lxml.etree.Element(_q("Identify"))
  lxml.etree.SubElement(e, _q("repositoryName")).text = _repositoryName
  lxml.etree.SubElement(e, _q("baseURL")).text = _baseUrl + "/oai"
  lxml.etree.SubElement(e, _q("protocolVersion")).text = "2.0"
  lxml.etree.SubElement(e, _q("adminEmail")).text = _adminEmail
  lxml.etree.SubElement(e, _q("earliestDatestamp")).text =\
    _formatTime(store.oaiGetEarliestUpdateTime())
  lxml.etree.SubElement(e, _q("deletedRecord")).text = "no"
  lxml.etree.SubElement(e, _q("granularity")).text = "YYYY-MM-DDThh:mm:ssZ"
  return _buildResponse(oaiRequest, e)

def _doListMetadataFormats (oaiRequest):
  e = lxml.etree.Element(_q("ListMetadataFormats"))
  mf = lxml.etree.SubElement(e, _q("metadataFormat"))
  lxml.etree.SubElement(mf, _q("metadataPrefix")).text = "oai_dc"
  lxml.etree.SubElement(mf, _q("schema")).text =\
    "http://www.openarchives.org/OAI/2.0/oai_dc.xsd"
  lxml.etree.SubElement(mf, _q("metadataNamespace")).text =\
    "http://www.openarchives.org/OAI/2.0/oai_dc/"
  mf = lxml.etree.SubElement(e, _q("metadataFormat"))
  lxml.etree.SubElement(mf, _q("metadataPrefix")).text = "datacite"
  lxml.etree.SubElement(mf, _q("schema")).text =\
    "http://schema.datacite.org/meta/kernel-3/metadata.xsd"
  lxml.etree.SubElement(mf, _q("metadataNamespace")).text =\
    "http://datacite.org/schema/kernel-3"
  return _buildResponse(oaiRequest, e)

def _doListSets (oaiRequest):
  if "resumptionToken" in oaiRequest[1]:
    return _error(oaiRequest, "badResumptionToken")
  else:
    return _error(oaiRequest, "noSetHierarchy")

def dispatch (request):
  if not _enabled:
    return django.http.HttpResponse("service unavailable", status=503,
      content_type="text/plain")
  oaiRequest = _buildRequest(request)
  if type(oaiRequest) is str:
    r = oaiRequest
  else:
    if oaiRequest[0] == "Identify":
      r = _doIdentify(oaiRequest)
    elif oaiRequest[0] == "ListMetadataFormats":
      r = _doListMetadataFormats(oaiRequest)
    elif oaiRequest[0] == "ListSets":
      r = _doListSets(oaiRequest)
    else:
      assert False, "unhandled case"
  return django.http.HttpResponse(r, content_type="text/xml; charset=UTF-8")
