# =============================================================================
#
# EZID :: datacite.py
#
# Interface to DataCite <http://www.datacite.org/>; specifically,
# interface to the SOAP services operated by the Technische
# Informationsbibliothek (TIB) <http://www.tib.uni-hannover.de/>.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2010, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import re
import urllib2
import xml.sax.saxutils

import config

_enabled = None
_soapUrl = None
_realm = None
_username = None
_password = None

def _loadConfig ():
  global _enabled, _soapUrl, _realm, _username, _password
  _enabled = (config.config("datacite.enabled").lower() == "true")
  _soapUrl = config.config("datacite.soap_url")
  _realm = config.config("datacite.realm")
  _username = config.config("datacite.username")
  _password = config.config("datacite.password")

_loadConfig()
config.addLoader(_loadConfig)

class SoapException (Exception):
  pass

def _soapRequest (request):
  if not _enabled: return ""
  h = urllib2.HTTPBasicAuthHandler()
  h.add_password(_realm, _soapUrl, _username, _password)
  o = urllib2.build_opener(h)
  r = urllib2.Request(_soapUrl)
  r.add_header("Content-Type", "text/xml; charset=UTF-8")
  r.add_header("SOAPAction", '""')
  r.add_data(request.encode("UTF-8"))
  c = o.open(r)
  s = c.read()
  c.close()
  # The following is not a particularly robust way of detecting faults
  # and extracting fault information, but... this whole SOAP interface
  # is going away soon anyway.
  if "<soap:Fault>" in s:
    m = re.search("<faultstring>(.*?)</faultstring>", s)
    if m:
      raise SoapException(m.group(1))
    else:
      raise SoapException("unknown SOAP fault")
  return s

def _interpolate (template, *args):
  return template % tuple(xml.sax.saxutils.escape(a) for a in args)

_registerTemplate = u"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope
  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:rs="RegServ"
  soapenv:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <soapenv:Body>
    <rs:registerDataDOI>
      <rs:arg0>%s</rs:arg0>
      <rs:arg1>%s</rs:arg1>
    </rs:registerDataDOI>
  </soapenv:Body>
</soapenv:Envelope>"""

def registerIdentifier (doi, targetUrl):
  """
  Registers a scheme-less DOI identifier (e.g., "10.5060/foo") and
  target URL (e.g., "http://whatever...") with DataCite.  No error
  checking is done on the inputs; in particular, it is not checked
  that the arguments are syntactically correct, nor is it checked that
  we have rights to the DOI prefix.
  """
  _soapRequest(_interpolate(_registerTemplate, doi, targetUrl))

_setTemplate = u"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope
  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:rs="RegServ"
  soapenv:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <soapenv:Body>
    <rs:updateURL>
      <rs:arg0>%s</rs:arg0>
      <rs:arg1>%s</rs:arg1>
    </rs:updateURL>
  </soapenv:Body>
</soapenv:Envelope>"""

def setTargetUrl (doi, targetUrl):
  """
  Sets the target URL of an existing scheme-less DOI identifier (e.g.,
  "10.5060/foo").  No error checking is done on the inputs.
  """
  _soapRequest(_interpolate(_setTemplate, doi, targetUrl))

_uploadTemplate = u"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope
  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:rs="RegServ"
  soapenv:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <soapenv:Body>
    <rs:updateCitationDOI>
      <rs:arg0>%s</rs:arg0>
    </rs:updateCitationDOI>
  </soapenv:Body>
</soapenv:Envelope>"""

# The following template is based on:
# http://datacite.org/schema/DataCite-MetadataKernel_v2.0.pdf

_metadataTemplate = u"""<?xml version="1.0" encoding="UTF-8"?>
<resource>
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
</resource>
"""

def uploadMetadata (doi, metadata):
  """
  Uploads citation metadata for the resource identified by an existing
  scheme-less DOI identifier (e.g., "10.5060/foo") to DataCite.  This
  same function can be used to overwrite previously-uploaded metadata.
  'metadata' should be a dictionary that maps metadata element names
  to values; note that only metadata elements from the DataCite
  profile (e.g., "datacite.title") are read.  No error checking is
  done on the inputs.
  """
  creator = metadata.get("datacite.creator", "")
  title = metadata.get("datacite.title", "")
  publisher = metadata.get("datacite.publisher", "")
  publicationYear = metadata.get("datacite.publicationyear", "")
  m = _interpolate(_metadataTemplate, doi, creator, title, publisher,
    publicationYear)
  _soapRequest(_interpolate(_uploadTemplate, m))

def identifierExists (doi):
  # TBD
  return False
