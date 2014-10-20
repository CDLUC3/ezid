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
import mapping
import shoulder

_lock = threading.Lock()
_enabled = None
_doiUrl = None
_metadataUrl = None
_numAttempts = None
_allocators = None
_stylesheet = None
_pingDoi = None
_pingTarget = None
_numActiveOperations = 0

def _loadConfig ():
  global _enabled, _doiUrl, _metadataUrl, _numAttempts, _allocators
  global _stylesheet, _pingDoi, _pingTarget
  _enabled = (config.config("datacite.enabled").lower() == "true")
  _doiUrl = config.config("datacite.doi_url")
  _metadataUrl = config.config("datacite.metadata_url")
  _numAttempts = int(config.config("datacite.num_attempts"))
  _allocators = {}
  for a in config.config("datacite.allocators").split(","):
    _allocators[a] = config.config("allocator_%s.password" % a)
  _stylesheet = lxml.etree.XSLT(lxml.etree.parse(os.path.join(
    django.conf.settings.PROJECT_ROOT, "profiles", "datacite.xsl")))
  _pingDoi = config.config("datacite.ping_doi")
  _pingTarget = config.config("datacite.ping_target")

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
  s = shoulder.getLongestMatch("doi:" + doi)
  # Should never happen.
  assert s is not None, "shoulder not found"
  a = s.datacenter.split(".")[0]
  p = _allocators.get(a, None)
  assert p is not None, "no such allocator: " + a
  return "Basic " + base64.b64encode(s.datacenter + ":" + p)

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
    except:
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

def getTargetUrl (doi):
  """
  Returns the target URL of a scheme-less DOI identifier (e.g.,
  "10.5060/foo") as registered with DataCite, or None if the
  identifier is not registered.
  """
  if not _enabled: return None
  # To hide transient network errors, we make multiple attempts.
  for i in range(_numAttempts):
    o = urllib2.build_opener(_HTTPErrorProcessor)
    r = urllib2.Request(_doiUrl + "/" + urllib.quote(doi))
    # We manually supply the HTTP Basic authorization header to avoid
    # the doubling of the number of HTTP transactions caused by the
    # challenge/response model.
    r.add_header("Authorization", _datacenterAuthorization(doi))
    c = None
    try:
      _modifyActiveCount(1)
      c = o.open(r)
      return c.read()
    except urllib2.HTTPError, e:
      if e.code == 404: return None
      if e.code != 500 or i == _numAttempts-1: raise e
    except:
      if i == _numAttempts-1: raise
    finally:
      _modifyActiveCount(-1)
      if c: c.close()

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

# From the DCMI Type Vocabulary
# <http://dublincore.org/documents/dcmi-type-vocabulary/#H7>:
_dcResourceTypes = ["Collection", "Dataset", "Event", "Image",
  "InteractiveResource", "MovingImage", "PhysicalObject", "Service",
  "Software", "Sound", "StillImage", "Text"]

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
    # Python shortcoming: local variables can't be assigned to from
    # inner scopes, so we have to make mappedMetadata a list.
    mappedMetadata = [None]
    def getMappedValue (element, index, label):
      if metadata.get("datacite."+element, "").strip() != "":
        return metadata["datacite."+element].strip()
      else:
        if mappedMetadata[0] == None:
          mappedMetadata[0] = mapping.getDisplayMetadata(metadata)
        assert mappedMetadata[0][index] != None, "no " + label
        return mappedMetadata[0][index]
    creator = getMappedValue("creator", 0, "creator")
    title = getMappedValue("title", 1, "title")
    publisher = getMappedValue("publisher", 2, "publisher")
    publicationYear = getMappedValue("publicationyear", 3, "publication year")
    m = re.match("(\d{4})(-\d\d)?(-\d\d)?$", publicationYear)
    if m:
      publicationYear = m.group(1)
    else:
      publicationYear = "0000"
    r = _interpolate(_metadataTemplate, doi, creator, title, publisher,
      publicationYear)
    if metadata.get("datacite.resourcetype", "").strip() != "":
      rt = metadata["datacite.resourcetype"].strip()
      if "/" in rt:
        gt, st = rt.split("/", 1)
        r += _interpolate(_resourceTypeTemplate2, gt.strip(), st.strip())
      else:
        r += _interpolate(_resourceTypeTemplate1, rt)
    elif metadata.get("_p", "") == "dc" and\
      metadata.get("dc.type", "").strip() != "":
      rt = metadata["dc.type"].strip()
      if rt in _dcResourceTypes:
        if rt in ["MovingImage", "StillImage"]: rt = "Image"
        r += _interpolate(_resourceTypeTemplate1, rt)
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
  try:
    oldRecord = _formRecord(doi, current)
  except AssertionError:
    oldRecord = None
  m = current.copy()
  m.update(delta)
  try:
    newRecord = _formRecord(doi, m)
  except AssertionError, e:
    return "DOI metadata requirements not satisfied: " + e.message
  if newRecord == oldRecord and not forceUpload: return None
  if not _enabled: return None
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
    except:
      if i == _numAttempts-1: raise
    else:
      return None
    finally:
      _modifyActiveCount(-1)
      if c: c.close()

def _deactivate (doi):
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
    except:
      if i == _numAttempts-1: raise
    else:
      break
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
  Raises an exception on error.
  """
  if not _enabled: return
  try:
    _deactivate(doi)
  except urllib2.HTTPError, e:
    if e.code == 404:
      # The identifier must already have metadata in DataCite; in case
      # it doesn't (as may be the case with legacy identifiers),
      # upload some bogus metadata.
      message = uploadMetadata(doi, {}, { "datacite.title": "inactive",
        "datacite.creator": "inactive", "datacite.publisher": "inactive",
        "datacite.publicationyear": "0000" })
      assert message is None,\
        "unexpected return from DataCite store metadata operation: " + message
      _deactivate(doi)
    else:
      raise

def ping ():
  """
  Tests the DataCite API (as well as the underlying Handle System),
  returning "up" or "down".
  """
  if not _enabled: return "up"
  try:
    r = setTargetUrl(_pingDoi, _pingTarget)
    assert r == None
  except:
    return "down"
  else:
    return "up"

def pingDataciteOnly ():
  """
  Tests the DataCite API (only), returning "up" or "down".
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
    except:
      if i == _numAttempts-1: return "down"
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
