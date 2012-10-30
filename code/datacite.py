# =============================================================================
#
# EZID :: datacite.py
#
# Interface to DataCite <http://www.datacite.org/>; specifically,
# interface to the DataCite Metadata Store <https://mds.datacite.org/>
# operated by the Technische Informationsbibliothek (TIB)
# <http://www.tib.uni-hannover.de/>.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2010, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import base64
import django.conf
import lxml.etree
import os.path
import re
import threading
import urllib
import urllib2
import xml.sax.saxutils

import config

_lock = threading.Lock()
_enabled = None
_doiUrl = None
_metadataUrl = None
_numAttempts = None
_datacenters = None
_prefixes = None
_stylesheet = None
_pingDoi = None
_pingTarget = None
_numActiveOperations = None

def _loadConfig ():
  global _enabled, _doiUrl, _metadataUrl, _numAttempts, _datacenters, _prefixes
  global _stylesheet, _pingDoi, _pingTarget, _numActiveOperations
  _enabled = (config.config("datacite.enabled").lower() == "true")
  _doiUrl = config.config("datacite.doi_url")
  _metadataUrl = config.config("datacite.metadata_url")
  _numAttempts = int(config.config("datacite.num_attempts"))
  _datacenters = {}
  for dc in config.config("datacite.datacenters").split(","):
    try:
      pw = config.config("datacenter_%s.password" % dc)
    except:
      pw = config.config("datacite.password")
    _datacenters[dc] = "Basic " +\
      base64.b64encode(config.config("datacenter_%s.name" % dc) + ":" + pw)
  _prefixes = dict((config.config("prefix_%s.prefix" % k)[4:],
    config.config("prefix_%s.datacenter" % k))\
    for k in config.config("prefixes.keys").split(",")\
    if config.config("prefix_%s.prefix" % k).startswith("doi:"))
  _stylesheet = lxml.etree.XSLT(lxml.etree.parse(os.path.join(
    django.conf.settings.PROJECT_ROOT, "profiles", "datacite.xsl")))
  _pingDoi = config.config("datacite.ping_doi")
  _pingTarget = config.config("datacite.ping_target")
  _lock.acquire()
  try:
    _numActiveOperations = 0
  finally:
    _lock.release()

_loadConfig()
config.addLoader(_loadConfig)

def _modifyActiveCount (delta):
  global _numActiveOperations
  _lock.acquire()
  try:
    _numActiveOperations += delta
  finally:
    _lock.release()

def numActiveOperations ():
  """
  Returns the number of active operations.
  """
  _lock.acquire()
  try:
    return _numActiveOperations
  finally:
    _lock.release()

class _HTTPErrorProcessor (urllib2.HTTPErrorProcessor):
  def http_response (self, request, response):
    # Bizarre that Python considers this an error.
    if response.code == 201:
      return response
    else:
      return urllib2.HTTPErrorProcessor.http_response(self, request, response)
  https_response = http_response

def _datacenterAuthorization (doi):
  prefix = None
  # Select the longest matching prefix.
  for p, dc in _prefixes.items():
    if doi.startswith(p) and (prefix is None or len(p) > len(prefix)):
      prefix = p
      datacenter = dc
  assert prefix is not None, "prefix not found"
  return _datacenters[datacenter]

def registerIdentifier (doi, targetUrl):
  """
  Registers a scheme-less DOI identifier (e.g., "10.5060/foo") and
  target URL (e.g., "http://whatever...") with DataCite.  There are
  three possible returns: None on success; a string error message if
  the target URL was not accepted by DataCite; or a thrown exception
  on other error.
  """
  if not _enabled: return None
  # To deal with transient problems with the Handle system underlying
  # the DataCite service, we make multiple attempts.
  for i in range(_numAttempts):
    o = urllib2.build_opener(_HTTPErrorProcessor)
    r = urllib2.Request(_doiUrl)
    # We manually supply the HTTP Basic authorization header to avoid
    # the doubling of the number of HTTP transactions caused by the
    # challenge/response model.
    r.add_header("Authorization", _datacenterAuthorization(doi))
    r.add_header("Content-Type", "text/plain; charset=UTF-8")
    r.add_data(("doi=%s\nurl=%s" % (doi.replace("\\", "\\\\"),
      targetUrl.replace("\\", "\\\\"))).encode("UTF-8"))
    c = None
    try:
      _modifyActiveCount(1)
      c = o.open(r)
      assert c.read() == "OK",\
        "unexpected return from DataCite register DOI operation"
    except urllib2.HTTPError, e:
      message = e.fp.read()
      if e.code == 400 and message.startswith("[url]"): return message
      if e.code != 500 or i == _numAttempts-1: raise e
    except urllib2.URLError:
      if i == _numAttempts-1: raise
    else:
      break
    finally:
      _modifyActiveCount(-1)
      if c: c.close()
  return None

def setTargetUrl (doi, targetUrl):
  """
  Sets the target URL of an existing scheme-less DOI identifier (e.g.,
  "10.5060/foo").  There are three possible returns: None on success;
  a string error message if the target URL was not accepted by
  DataCite; or a thrown exception on other error.
  """
  return registerIdentifier(doi, targetUrl)

_prologRE = re.compile("(<\?xml\s+version\s*=\s*['\"]([-\w.:]+)[\"'])" +\
  "(\s+encoding\s*=\s*['\"]([-\w.]+)[\"'])?")
_utf8RE = re.compile("UTF-?8$", re.I)
_rootTagRE =\
  re.compile("{(http://datacite\.org/schema/kernel-[^}]*)}resource$")

def validateDcmsRecord (identifier, record):
  """
  Validates and normalizes a DataCite Metadata Scheme
  <http://schema.datacite.org/> record for a qualified identifier
  (e.g., "doi:10.5060/foo").  The record should be unencoded.  Either
  the normalized record is returned or an assertion error is raised.
  Validation is limited to checking that the record is well-formed
  XML, that the record appears to be a DCMS record (by examining the
  root element), and that the identifier type embedded in the record
  matches that of 'identifier'.  (In an extension to DCMS, we allow
  the identifier to be something other than a DOI, for example, an
  ARK.)  Normalization is limited to removing any encoding
  declaration.  'identifier' is inserted in the returned record.
  """
  m = _prologRE.match(record)
  if m:
    assert m.group(2) == "1.0", "unsupported XML version"
    if m.group(3) != None:
      assert _utf8RE.match(m.group(4)), "XML encoding must be UTF-8"
      record = record[:len(m.group(1))] +\
        record[len(m.group(1))+len(m.group(3)):]
  else:
    record = "<?xml version=\"1.0\"?>\n" + record
  try:
    root = lxml.etree.XML(record)
  except Exception, e:
    assert False, "XML parse error: " + str(e)
  m = _rootTagRE.match(root.tag)
  assert m, "not a DataCite record"
  i = root.xpath("N:identifier", namespaces={ "N": m.group(1) })
  assert len(i) == 1 and "identifierType" in i[0].attrib,\
    "not a valid DataCite record"
  if identifier.startswith("doi:"):
    type = "DOI"
    identifier = identifier[4:]
  elif identifier.startswith("ark:/"):
    type = "ARK"
    identifier = identifier[5:]
  elif identifier.startswith("urn:uuid:"):
    type = "URN:UUID"
    identifier = identifier[9:]
  else:
    assert False, "unrecognized identifier scheme"
  assert i[0].attrib["identifierType"] == type, "identifier type mismatch"
  i[0].text = identifier
  try:
    return "<?xml version=\"1.0\"?>\n" +\
      lxml.etree.tostring(root, encoding=unicode)
  except Exception, e:
    assert False, "XML serialization error: " + str(e)

# From version 2.2 of the DataCite Metadata Schema <doi:10.5438/0005>:
_resourceTypes = ["Collection", "Dataset", "Event", "Film", "Image",
  "InteractiveResource", "Model", "PhysicalObject", "Service", "Software",
  "Sound", "Text"]

def validateResourceType (descriptor):
  """
  Validates and normalizes a resource type descriptor.  By
  "descriptor" we mean either a general resource type by itself (e.g.,
  "Image") or a general and a specific resource type separated by a
  slash (e.g., "Image/Photograph").  Either a normalized descriptor is
  returned or an assertion error is raised.
  """
  descriptor = descriptor.strip()
  if "/" in descriptor:
    gt, st = descriptor.split("/", 1)
    gt = gt.strip()
    st = st.strip()
    assert gt in _resourceTypes, "invalid general resource type"
    if len(st) > 0:
      return gt + "/" + st
    else:
      return gt
  else:
    assert descriptor in _resourceTypes, "invalid general resource type"
    return descriptor

def _insertEncodingDeclaration (record):
  m = _prologRE.match(record)
  if m:
    if m.group(3) is None:
      return record[:len(m.group(1))] + " encoding=\"UTF-8\"" +\
        record[len(m.group(1)):]
    else:
      return record
  else:
    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" + record

def _interpolate (template, *args):
  return template % tuple(xml.sax.saxutils.escape(a, { "\"": "&quot;" })\
    for a in args)

_metadataTemplate = u"""<?xml version="1.0" encoding="UTF-8"?>
<resource xmlns="http://datacite.org/schema/kernel-2.2"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://datacite.org/schema/kernel-2.2
    http://schema.datacite.org/meta/kernel-2.2/metadata.xsd">
  <identifier identifierType="DOI">%s</identifier>
  <creators>
    <creator>
      <creatorName>%s</creatorName>
    </creator>
  </creators>
  <titles>
    <title>%s</title>
  </titles>
  <publisher>%s</publisher>
  <publicationYear>%s</publicationYear>
"""

_resourceTypeTemplate1 = u"""  <resourceType resourceTypeGeneral="%s"/>
"""

_resourceTypeTemplate2 =\
  u"""  <resourceType resourceTypeGeneral="%s">%s</resourceType>
"""

def _formRecord (doi, metadata):
  if metadata.get("datacite", "").strip() != "":
    return _insertEncodingDeclaration(metadata["datacite"])
  else:
    m = {}
    for f in ["creator", "title", "publisher", "publicationyear",
      "resourcetype"]:
      if metadata.get("datacite."+f, "").strip() != "":
        m[f] = metadata["datacite."+f].strip()
      else:
        m[f] = "none supplied"
    if not re.match("\d{4}$", m["publicationyear"]):
      m["publicationyear"] = "0000"
    r = _interpolate(_metadataTemplate, doi, m["creator"], m["title"],
      m["publisher"], m["publicationyear"])
    if m["resourcetype"] != "none supplied":
      if "/" in m["resourcetype"]:
        gt, st = m["resourcetype"].split("/", 1)
        r += _interpolate(_resourceTypeTemplate2, gt.strip(), st.strip())
      else:
        r += _interpolate(_resourceTypeTemplate1, m["resourcetype"])
    r += u"</resource>\n"
    return r

def uploadMetadata (doi, current, delta, forceUpload=False):
  """
  Uploads citation metadata for the resource identified by an existing
  scheme-less DOI identifier (e.g., "10.5060/foo") to DataCite.  This
  same function can be used to overwrite previously-uploaded metadata.
  'current' and 'delta' should be dictionaries mapping metadata
  element names (e.g., "Title") to values.  'current+delta' is
  uploaded, but only if there is at least one DataCite-relevant
  difference between it and 'current' alone (unless 'forceUpload' is
  true).  There are three possible returns: None on success; a string
  error message if the uploaded DataCite Metadata Scheme record was
  not accepted by DataCite (due to an XML-related problem); or a
  thrown exception on other error.  No error checking is done on the
  inputs.
  """
  if not _enabled: return None
  oldRecord = _formRecord(doi, current)
  m = current.copy()
  m.update(delta)
  newRecord = _formRecord(doi, m)
  if newRecord == oldRecord and not forceUpload: return None
  # To hide transient network errors, we make multiple attempts.
  for i in range(_numAttempts):
    o = urllib2.build_opener(_HTTPErrorProcessor)
    r = urllib2.Request(_metadataUrl)
    # We manually supply the HTTP Basic authorization header to avoid
    # the doubling of the number of HTTP transactions caused by the
    # challenge/response model.
    r.add_header("Authorization", _datacenterAuthorization(doi))
    r.add_header("Content-Type", "application/xml; charset=UTF-8")
    r.add_data(newRecord.encode("UTF-8"))
    c = None
    try:
      _modifyActiveCount(1)
      c = o.open(r)
      assert c.read().startswith("OK"),\
        "unexpected return from DataCite store metadata operation"
    except urllib2.HTTPError, e:
      message = e.fp.read()
      if e.code == 400 and (message.startswith("[xml]") or\
        message.startswith("ParseError")):
        return "element 'datacite': " + message
      else:
        raise e
    except urllib2.URLError:
      if i == _numAttempts-1: raise
    else:
      return None
    finally:
      _modifyActiveCount(-1)
      if c: c.close()

def deactivate (doi):
  """
  Deactivates an existing, scheme-less DOI identifier (e.g.,
  "10.5060/foo") in DataCite.  This removes the identifier from
  DataCite's search index, but has no effect on the identifier's
  existence in the Handle system or on the ability to change the
  identifier's target URL.  The identifier can and will be reactivated
  by uploading new metadata to it (cf. uploadMetadata in this module).
  Raises an exception an error.
  """
  if not _enabled: return
  # The identifier must already have metadata in DataCite; in case it
  # doesn't, upload some bogus metadata.
  message = uploadMetadata(doi, {}, { "datacite.title": "inactive" })
  assert message is None,\
    "unexpected return from DataCite store metadata operation: " + message
  # To hide transient network errors, we make multiple attempts.
  for i in range(_numAttempts):
    o = urllib2.build_opener(_HTTPErrorProcessor)
    r = urllib2.Request(_metadataUrl + "/" + urllib.quote(doi))
    # We manually supply the HTTP Basic authorization header to avoid
    # the doubling of the number of HTTP transactions caused by the
    # challenge/response model.
    r.add_header("Authorization", _datacenterAuthorization(doi))
    r.get_method = lambda: "DELETE"
    c = None
    try:
      _modifyActiveCount(1)
      c = o.open(r)
      assert c.read() == "OK",\
        "unexpected return from DataCite deactivate DOI operation"
    except urllib2.HTTPError, e:
      if e.code != 500 or i == _numAttempts-1: raise e
    except urllib2.URLError:
      if i == _numAttempts-1: raise
    else:
      break
    finally:
      _modifyActiveCount(-1)
      if c: c.close()

def ping ():
  """
  Tests the DataCite API, returning "up" or "down".
  """
  if not _enabled: return "up"
  # To hide transient network errors, we make multiple attempts.
  for i in range(_numAttempts):
    o = urllib2.build_opener(_HTTPErrorProcessor)
    r = urllib2.Request(_doiUrl + "/" + _pingDoi)
    # We manually supply the HTTP Basic authorization header to avoid
    # the doubling of the number of HTTP transactions caused by the
    # challenge/response model.
    r.add_header("Authorization", _datacenterAuthorization(_pingDoi))
    c = None
    try:
      _modifyActiveCount(1)
      c = o.open(r)
      assert c.read() == _pingTarget
    except urllib2.URLError:
      if i == _numAttempts-1: return "down"
    except:
      return "down"
    else:
      return "up"
    finally:
      _modifyActiveCount(-1)
      if c: c.close()

def _removeEncodingDeclaration (record):
  m = _prologRE.match(record)
  if m and m.group(3) != None:
    return record[:len(m.group(1))] + record[len(m.group(1))+len(m.group(3)):]
  else:
    return record

def dcmsRecordToHtml (record):
  """
  Converts a DataCite Metadata Scheme <http://schema.datacite.org/>
  record to an XHTML table.  The record should be unencoded.  Returns
  None on error.
  """
  try:
    r = lxml.etree.tostring(_stylesheet(lxml.etree.XML(
      _removeEncodingDeclaration(record))), encoding=unicode)
    assert r.startswith("<table")
    return r
  except:
    return None
