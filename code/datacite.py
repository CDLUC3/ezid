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
import os
import os.path
import re
import threading
import time
import urllib
import urllib2
import xml.sax.saxutils

import config
import ezidapp.models
import ezidapp.models.validation
import mapping
import util

_lock = threading.Lock()
_enabled = None
_doiUrl = None
_metadataUrl = None
_numAttempts = None
_reattemptDelay = None
_timeout = None
_allocators = None
_stylesheet = None
_crossrefTransform = None
_pingDoi = None
_pingDatacenter = None
_pingTarget = None
_numActiveOperations = 0
_schemas = None

def _loadConfig ():
  global _enabled, _doiUrl, _metadataUrl, _numAttempts, _reattemptDelay
  global _timeout, _allocators, _stylesheet, _crossrefTransform, _pingDoi
  global _pingDatacenter, _pingTarget, _schemas
  _enabled = (config.get("datacite.enabled").lower() == "true")
  _doiUrl = config.get("datacite.doi_url")
  _metadataUrl = config.get("datacite.metadata_url")
  _numAttempts = int(config.get("datacite.num_attempts"))
  _reattemptDelay = int(config.get("datacite.reattempt_delay"))
  _timeout = int(config.get("datacite.timeout"))
  _allocators = {}
  for a in config.get("datacite.allocators").split(","):
    _allocators[a] = config.get("allocator_%s.password" % a)
  _stylesheet = lxml.etree.XSLT(lxml.etree.parse(os.path.join(
    django.conf.settings.PROJECT_ROOT, "profiles", "datacite.xsl")))
  _crossrefTransform = lxml.etree.XSLT(lxml.etree.parse(os.path.join(
    django.conf.settings.PROJECT_ROOT, "profiles", "crossref2datacite.xsl")))
  _pingDoi = config.get("datacite.ping_doi")
  _pingDatacenter = config.get("datacite.ping_datacenter")
  _pingTarget = config.get("datacite.ping_target")
  schemas = {}
  for f in os.listdir(os.path.join(django.conf.settings.PROJECT_ROOT, "xsd")):
    m = re.match("datacite-kernel-(.*)", f)
    if m:
      schemas[m.group(1)] = (lxml.etree.XMLSchema(lxml.etree.parse(
        os.path.join(django.conf.settings.PROJECT_ROOT, "xsd", f,
        "metadata.xsd"))), threading.Lock())
  _schemas = schemas

_loadConfig()
config.registerReloadListener(_loadConfig)

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

def _authorization (doi, datacenter=None):
  if datacenter == None:
    s = ezidapp.models.getLongestShoulderMatch("doi:" + doi)
    # Should never happen.
    assert s is not None, "shoulder not found"
    datacenter = s.datacenter.symbol
  a = datacenter.split(".")[0]
  p = _allocators.get(a, None)
  assert p is not None, "no such allocator: " + a
  return "Basic " + base64.b64encode(datacenter + ":" + p)

def registerIdentifier (doi, targetUrl, datacenter=None):
  """
  Registers a scheme-less DOI identifier (e.g., "10.5060/FOO") and
  target URL (e.g., "http://whatever...") with DataCite.
  'datacenter', if specified, should be the identifier's datacenter,
  e.g., "CDL.BUL".  There are three possible returns: None on success;
  a string error message if the target URL was not accepted by
  DataCite; or a thrown exception on other error.
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
    r.add_header("Authorization", _authorization(doi, datacenter))
    r.add_header("Content-Type", "text/plain; charset=UTF-8")
    r.add_data(("doi=%s\nurl=%s" % (doi.replace("\\", "\\\\"),
      targetUrl.replace("\\", "\\\\"))).encode("UTF-8"))
    c = None
    try:
      _modifyActiveCount(1)
      c = o.open(r, timeout=_timeout)
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
    time.sleep(_reattemptDelay)
  return None

def setTargetUrl (doi, targetUrl, datacenter=None):
  """
  Sets the target URL of an existing scheme-less DOI identifier (e.g.,
  "10.5060/FOO").  'datacenter', if specified, should be the
  identifier's datacenter, e.g., "CDL.BUL".  There are three possible
  returns: None on success; a string error message if the target URL
  was not accepted by DataCite; or a thrown exception on other error.
  """
  return registerIdentifier(doi, targetUrl, datacenter)

def getTargetUrl (doi, datacenter=None):
  """
  Returns the target URL of a scheme-less DOI identifier (e.g.,
  "10.5060/FOO") as registered with DataCite, or None if the
  identifier is not registered.  'datacenter', if specified, should be
  the identifier's datacenter, e.g., "CDL.BUL".
  """
  # To hide transient network errors, we make multiple attempts.
  for i in range(_numAttempts):
    o = urllib2.build_opener(_HTTPErrorProcessor)
    r = urllib2.Request(_doiUrl + "/" + urllib.quote(doi))
    # We manually supply the HTTP Basic authorization header to avoid
    # the doubling of the number of HTTP transactions caused by the
    # challenge/response model.
    r.add_header("Authorization", _authorization(doi, datacenter))
    c = None
    try:
      _modifyActiveCount(1)
      c = o.open(r, timeout=_timeout)
      return c.read()
    except urllib2.HTTPError, e:
      if e.code == 404: return None
      if e.code != 500 or i == _numAttempts-1: raise e
    except:
      if i == _numAttempts-1: raise
    finally:
      _modifyActiveCount(-1)
      if c: c.close()
    time.sleep(_reattemptDelay)

_prologRE = re.compile("(<\?xml\s+version\s*=\s*['\"]([-\w.:]+)[\"'])" +\
  "(\s+encoding\s*=\s*['\"]([-\w.]+)[\"'])?")
_utf8RE = re.compile("UTF-?8$", re.I)
_rootTagRE =\
  re.compile("{(http://datacite\.org/schema/kernel-([^}]*))}resource$")

def validateDcmsRecord (identifier, record, schemaValidate=True):
  """
  Validates and normalizes a DataCite Metadata Scheme
  <http://schema.datacite.org/> record for a qualified identifier
  (e.g., "doi:10.5060/FOO").  The record should be unencoded.  Either
  the normalized record is returned or an assertion error is raised.
  If 'schemaValidate' is true, the record is validated against the
  appropriate XML schema; otherwise, only a more forgiving
  well-formedness check is performed.  (In an extension to DCMS, we
  allow the identifier to be something other than a DOI, for example,
  an ARK.)  The record is normalized by removing any encoding
  declaration; by converting from schema version 2.1 to 2.2 if
  necessary; and by inserting an appropriate 'schemaLocation'
  attribute.  Also, 'identifier' is inserted in the returned record.
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
  # We first do an initial parsing of the record to check
  # well-formedness and to be able to manipulate it, but hold off on
  # full schema validation because of our extension to the schema to
  # include other identifier types.
  try:
    root = lxml.etree.XML(record)
  except Exception, e:
    assert False, "XML parse error: " + str(e)
  m = _rootTagRE.match(root.tag)
  assert m, "not a DataCite record"
  version = m.group(2)
  # As a special case, upgrade schema version 2.1 to 2.2.
  if version == "2.1":
    def changeNamespace (node):
      # The order is important here: parent before children.
      node.tag = "{http://datacite.org/schema/kernel-2.2}" +\
        node.tag.split("}")[1]
      for child in node: changeNamespace(child)
    changeNamespace(root)
    lxml.etree.cleanup_namespaces(root)
    m = _rootTagRE.match(root.tag)
    version = "2.2"
  schema = _schemas.get(version, None)
  assert schema != None, "unsupported DataCite record version"
  i = root.xpath("N:identifier", namespaces={ "N": m.group(1) })
  assert len(i) == 1 and "identifierType" in i[0].attrib,\
    "malformed DataCite record: no <identifier> element"
  i = i[0]
  if identifier.startswith("doi:"):
    type = "DOI"
    identifier = identifier[4:]
  elif identifier.startswith("ark:/"):
    type = "ARK"
    identifier = identifier[5:]
  elif identifier.startswith("uuid:"):
    type = "UUID"
    identifier = identifier[5:]
  else:
    assert False, "unrecognized identifier scheme"
  assert i.attrib["identifierType"] == type,\
    "mismatch between identifier type and <identifier> element"
  if schemaValidate:
    # We temporarily replace the identifier with something innocuous
    # that will pass the schema's validation check, then change it
    # back.  Locking lameness: despite its claims, XMLSchema objects
    # are in fact not threadsafe.
    i.attrib["identifierType"] = "DOI"
    i.text = "10.1234/X"
    schema[1].acquire()
    try:
      schema[0].assert_(root)
    except Exception:
      # Ouch.  On some LXML installations, but not all, an error is
      # "sticky" and, unless it is cleared out, will be returned
      # repeatedly regardless of what new error is encountered.
      schema[0]._clear_error_log()
      raise
    finally:
      schema[1].release()
    i.attrib["identifierType"] = type
  i.text = identifier
  root.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"] =\
    ("http://datacite.org/schema/kernel-%s " +\
    "http://schema.datacite.org/meta/kernel-%s/metadata.xsd") %\
    (version, version)
  try:
    # We re-sanitize the document because unacceptable characters can
    # be (and have been) introduced via XML character entities.
    return "<?xml version=\"1.0\"?>\n" +\
      util.sanitizeXmlSafeCharset(lxml.etree.tostring(root, encoding=unicode))
  except Exception, e:
    assert False, "XML serialization error: " + str(e)

def _interpolate (template, *args):
  return template % tuple(xml.sax.saxutils.escape(a, { "\"": "&quot;" })\
    for a in args)

_metadataTemplate = u"""<?xml version="1.0" encoding="UTF-8"?>
<resource xmlns="http://datacite.org/schema/kernel-4"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://datacite.org/schema/kernel-4
    http://schema.datacite.org/meta/kernel-4/metadata.xsd">
  <identifier identifierType="%s">%s</identifier>
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

def formRecord (identifier, metadata, supplyMissing=False):
  """
  Forms an XML record for upload to DataCite, employing metadata
  mapping if necessary.  'identifier' should be a qualified identifier
  (e.g., "doi:10.5060/FOO").  'metadata' should be the identifier's
  metadata as a dictionary of (name, value) pairs.  Returns an XML
  document as a Unicode string.  The document contains a UTF-8
  encoding declaration, but is not in fact encoded.  If
  'supplyMissing' is true, the "(:unav)" code is supplied for missing
  required metadata fields; otherwise, missing metadata results in an
  assertion error being raised.
  """
  if identifier.startswith("doi:"):
    idType = "DOI"
    idBody = identifier[4:]
  elif identifier.startswith("ark:/"):
    idType = "ARK"
    idBody = identifier[5:]
  elif identifier.startswith("uuid:"):
    idType = "UUID"
    idBody = identifier[5:]
  else:
    assert False, "unhandled case"
  if metadata.get("datacite", "").strip() != "":
    return util.insertXmlEncodingDeclaration(metadata["datacite"])
  elif metadata.get("_p", metadata.get("_profile", "")) == "crossref" and\
    metadata.get("crossref", "").strip() != "":
    # We could run Crossref metadata through the metadata mapper using
    # the case below, but doing it this way creates a richer XML
    # record.
    overrides = { "_idType": idType, "_id": idBody }
    for e in ["creator", "title", "publisher", "publicationyear",
      "resourcetype"]:
      if metadata.get("datacite."+e, "").strip() != "":
        overrides["datacite."+e] = metadata["datacite."+e].strip()
    if "datacite.publicationyear" in overrides:
      try:
        overrides["datacite.publicationyear"] =\
          ezidapp.models.validation.publicationDate(
          overrides["datacite.publicationyear"])[:4]
      except:
        overrides["datacite.publicationyear"] = "0000"
    try:
      return util.insertXmlEncodingDeclaration(crossrefToDatacite(
        metadata["crossref"].strip(), overrides))
    except Exception, e:
      assert False, "Crossref to DataCite metadata conversion error: " + str(e)
  else:
    km = mapping.map(metadata, datacitePriority=True)
    for a in ["creator", "title", "publisher", "date"]:
      if getattr(km, a) == None:
        if supplyMissing:
          setattr(km, a, "(:unav)")
        else:
          assert False, "no " + ("publication date" if a == "date" else a)
    d = km.validatedDate
    r = _interpolate(_metadataTemplate, idType, idBody, km.creator, km.title,
      km.publisher, d[:4] if d else "0000")
    t = km.validatedType
    if t == None:
      if km.type != None:
        t = "Other"
      else:
        t = "Other/(:unav)"
    if "/" in t:
      gt, st = t.split("/", 1)
      r += _interpolate(_resourceTypeTemplate2, gt, st)
    else:
      r += _interpolate(_resourceTypeTemplate1, t)
    r += u"</resource>\n"
    return r

def uploadMetadata (doi, current, delta, forceUpload=False, datacenter=None):
  """
  Uploads citation metadata for the resource identified by an existing
  scheme-less DOI identifier (e.g., "10.5060/FOO") to DataCite.  This
  same function can be used to overwrite previously-uploaded metadata.
  'current' and 'delta' should be dictionaries mapping metadata
  element names (e.g., "Title") to values.  'current+delta' is
  uploaded, but only if there is at least one DataCite-relevant
  difference between it and 'current' alone (unless 'forceUpload' is
  true).  'datacenter', if specified, should be the identifier's
  datacenter, e.g., "CDL.BUL".  There are three possible returns: None
  on success; a string error message if the uploaded DataCite Metadata
  Scheme record was not accepted by DataCite (due to an XML-related
  problem); or a thrown exception on other error.  No error checking
  is done on the inputs.
  """
  try:
    oldRecord = formRecord("doi:" + doi, current)
  except AssertionError:
    oldRecord = None
  m = current.copy()
  m.update(delta)
  try:
    newRecord = formRecord("doi:" + doi, m)
  except AssertionError, e:
    return "DOI metadata requirements not satisfied: " + str(e)
  if newRecord == oldRecord and not forceUpload: return None
  if not _enabled: return None
  # To hide transient network errors, we make multiple attempts.
  for i in range(_numAttempts):
    o = urllib2.build_opener(_HTTPErrorProcessor)
    r = urllib2.Request(_metadataUrl)
    # We manually supply the HTTP Basic authorization header to avoid
    # the doubling of the number of HTTP transactions caused by the
    # challenge/response model.
    r.add_header("Authorization", _authorization(doi, datacenter))
    r.add_header("Content-Type", "application/xml; charset=UTF-8")
    r.add_data(newRecord.encode("UTF-8"))
    c = None
    try:
      _modifyActiveCount(1)
      c = o.open(r, timeout=_timeout)
      assert c.read().startswith("OK"),\
        "unexpected return from DataCite store metadata operation"
    except urllib2.HTTPError, e:
      message = e.fp.read()
      if e.code == 400 and (message.startswith("[xml]") or\
        message.startswith("ParseError")):
        return "element 'datacite': " + message
      if e.code != 500 or i == _numAttempts-1: raise e
    except:
      if i == _numAttempts-1: raise
    else:
      return None
    finally:
      _modifyActiveCount(-1)
      if c: c.close()
    time.sleep(_reattemptDelay)

def _deactivate (doi, datacenter):
  # To hide transient network errors, we make multiple attempts.
  for i in range(_numAttempts):
    o = urllib2.build_opener(_HTTPErrorProcessor)
    r = urllib2.Request(_metadataUrl + "/" + urllib.quote(doi))
    # We manually supply the HTTP Basic authorization header to avoid
    # the doubling of the number of HTTP transactions caused by the
    # challenge/response model.
    r.add_header("Authorization", _authorization(doi, datacenter))
    r.get_method = lambda: "DELETE"
    c = None
    try:
      _modifyActiveCount(1)
      c = o.open(r, timeout=_timeout)
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
    time.sleep(_reattemptDelay)

def deactivate (doi, datacenter=None):
  """
  Deactivates an existing, scheme-less DOI identifier (e.g.,
  "10.5060/FOO") in DataCite.  This removes the identifier from
  DataCite's search index, but has no effect on the identifier's
  existence in the Handle system or on the ability to change the
  identifier's target URL.  The identifier can and will be reactivated
  by uploading new metadata to it (cf. uploadMetadata in this module).
  'datacenter', if specified, should be the identifier's datacenter,
  e.g., "CDL.BUL".  Returns None; raises an exception on error.
  """
  if not _enabled: return
  try:
    _deactivate(doi, datacenter)
  except urllib2.HTTPError, e:
    if e.code == 404:
      # The identifier must already have metadata in DataCite; in case
      # it doesn't (as may be the case with legacy identifiers),
      # upload some bogus metadata.
      message = uploadMetadata(doi, {}, { "datacite.title": "inactive",
        "datacite.creator": "inactive", "datacite.publisher": "inactive",
        "datacite.publicationyear": "0000" }, datacenter=datacenter)
      assert message is None,\
        "unexpected return from DataCite store metadata operation: " + message
      _deactivate(doi, datacenter)
    else:
      raise
  return None

def ping ():
  """
  Tests the DataCite API (as well as the underlying Handle System),
  returning "up" or "down".
  """
  if not _enabled: return "up"
  try:
    r = setTargetUrl(_pingDoi, _pingTarget, _pingDatacenter)
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
    r.add_header("Authorization", _authorization(_pingDoi, _pingDatacenter))
    c = None
    try:
      _modifyActiveCount(1)
      c = o.open(r, timeout=_timeout)
      assert c.read() == _pingTarget
    except:
      if i == _numAttempts-1: return "down"
    else:
      return "up"
    finally:
      _modifyActiveCount(-1)
      if c: c.close()
    time.sleep(_reattemptDelay)

def dcmsRecordToHtml (record):
  """
  Converts a DataCite Metadata Scheme <http://schema.datacite.org/>
  record to an XHTML table.  The record should be unencoded.  Returns
  None on error.
  """
  try:
    r = lxml.etree.tostring(_stylesheet(util.parseXmlString(record)),
      encoding=unicode)
    assert r.startswith("<table")
    return r
  except:
    return None

def crossrefToDatacite (record, overrides={}):
  """
  Converts a Crossref Deposit Schema
  <http://help.crossref.org/deposit_schema> document to a DataCite
  Metadata Scheme <http://schema.datacite.org/> record.  'overrides'
  is a dictionary of individual metadata element names (e.g.,
  "datacite.title") and values that override the conversion values
  that would normally be drawn from the input document.  Throws an
  exception on error.
  """
  d = {}
  for k, v in overrides.items():
    d[k] = lxml.etree.XSLT.strparam(v)
  return lxml.etree.tostring(_crossrefTransform(
    util.parseXmlString(record), **d), encoding=unicode)

_schemaVersionRE =\
  re.compile("{http://datacite\.org/schema/kernel-([^}]*)}resource$")

def upgradeDcmsRecord (record, returnString=True):
  """
  Converts a DataCite Metadata Scheme <http://schema.datacite.org/>
  record (supplied as an unencoded Unicode string) to the latest
  version of the schema (currently, version 4).  If 'returnString' is
  true, the record is returned as an unencoded Unicode string, in
  which case the record has no XML declaration.  Otherwise, an
  lxml.etree.Element object is returned.  In both cases, the root
  element's xsi:schemaLocation attribute is set or added as necessary.
  """
  root = util.parseXmlString(record)
  root.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"] =\
    "http://datacite.org/schema/kernel-4 " +\
    "http://schema.datacite.org/meta/kernel-4/metadata.xsd"
  m = _schemaVersionRE.match(root.tag)
  if m.group(1) == "4":
    # Nothing to do.
    if returnString:
      return lxml.etree.tostring(root, encoding=unicode)
    else:
      return root
  def q (elementName):
    return "{http://datacite.org/schema/kernel-4}" + elementName
  def changeNamespace (node):
    if node.tag is not lxml.etree.Comment:
      # The order is important here: parent before children.
      node.tag = q(node.tag.split("}")[1])
      for child in node: changeNamespace(child)
  changeNamespace(root)
  ns = { "N": "http://datacite.org/schema/kernel-4" }
  # Resource type is required as of version 4.
  e = root.xpath("//N:resourceType", namespaces=ns)
  assert len(e) <= 1
  if len(e) == 1:
    if e[0].attrib["resourceTypeGeneral"] == "Film":
      e[0].attrib["resourceTypeGeneral"] = "Audiovisual"
  else:
    e = lxml.etree.SubElement(root, q("resourceType"))
    e.attrib["resourceTypeGeneral"] = "Other"
    e.text = "(:unav)"
  # There's no way to assign new types to start and end dates, so just
  # delete them.
  for e in root.xpath("//N:date", namespaces=ns):
    if e.attrib["dateType"] in ["StartDate", "EndDate"]:
      e.getparent().remove(e)
  for e in root.xpath("//N:dates", namespaces=ns):
    if len(e) == 0: e.getparent().remove(e)
  # The contributor type "Funder" went away in version 4.
  for e in root.xpath("//N:contributor[@contributorType='Funder']",
    namespaces=ns):
    fr = root.xpath("//N:fundingReferences", namespaces=ns)
    if len(fr) > 0:
      fr = fr[0]
    else:
      fr = lxml.etree.SubElement(root, q("fundingReferences"))
    for n in e.xpath("N:contributorName", namespaces=ns):
      lxml.etree.SubElement(lxml.etree.SubElement(fr, q("fundingReference")),
        q("funderName")).text = n.text
    e.getparent().remove(e)
  for e in root.xpath("//N:contributors", namespaces=ns):
    if len(e) == 0: e.getparent().remove(e)
  # Geometry changes in version 4.
  for e in root.xpath("//N:geoLocationPoint", namespaces=ns):
    if len(e) == 0:
      coords = e.text.split()
      if len(coords) == 2:
        lxml.etree.SubElement(e, q("pointLongitude")).text = coords[1]
        lxml.etree.SubElement(e, q("pointLatitude")).text = coords[0]
        e.text = None
      else:
        # Should never happen.
        e.getparent().remove(e)
  for e in root.xpath("//N:geoLocationBox", namespaces=ns):
    if len(e) == 0:
      coords = e.text.split()
      if len(coords) == 4:
        lxml.etree.SubElement(e, q("westBoundLongitude")).text = coords[1]
        lxml.etree.SubElement(e, q("eastBoundLongitude")).text = coords[3]
        lxml.etree.SubElement(e, q("southBoundLatitude")).text = coords[0]
        lxml.etree.SubElement(e, q("northBoundLatitude")).text = coords[2]
        e.text = None
      else:
        # Should never happen.
        e.getparent().remove(e)
  lxml.etree.cleanup_namespaces(root)
  if returnString:
    return lxml.etree.tostring(root, encoding=unicode)
  else:
    return root
