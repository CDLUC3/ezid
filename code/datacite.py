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
import re
import urllib2
import xml.sax.saxutils

import config

_enabled = None
_doiUrl = None
_metadataUrl = None
_auth = None

def _loadConfig ():
  global _enabled, _doiUrl, _metadataUrl, _auth
  _enabled = (config.config("datacite.enabled").lower() == "true")
  _doiUrl = config.config("datacite.doi_url")
  _metadataUrl = config.config("datacite.metadata_url")
  datacenter = config.config("datacite.datacenter")
  password = config.config("datacite.password")
  _auth = "Basic " + base64.b64encode(datacenter + ":" + password)

_loadConfig()
config.addLoader(_loadConfig)

class _HTTPErrorProcessor (urllib2.HTTPErrorProcessor):
  def http_response (self, request, response):
    # Bizarre that Python considers this an error.
    if response.code == 201:
      return response
    else:
      return urllib2.HTTPErrorProcessor.http_response(self, request, response)
  https_response = http_response

def registerIdentifier (doi, targetUrl):
  """
  Registers a scheme-less DOI identifier (e.g., "10.5060/foo") and
  target URL (e.g., "http://whatever...") with DataCite.  No error
  checking is done on the inputs; in particular, it is not checked
  that the arguments are syntactically correct, nor is it checked that
  we have rights to the DOI prefix.
  """
  o = urllib2.build_opener(_HTTPErrorProcessor)
  r = urllib2.Request(_doiUrl)
  # We manually supply the HTTP Basic authorization header to avoid
  # the doubling of the number of HTTP transactions caused by the
  # challenge/response model.
  r.add_header("Authorization", _auth)
  r.add_header("Content-Type", "text/plain; charset=UTF-8")
  r.add_data(("doi=%s\nurl=%s" % (doi, targetUrl)).encode("UTF-8"))
  c = o.open(r)
  assert c.read() == "OK",\
    "unexpected return from DataCite register DOI operation"
  c.close()

def setTargetUrl (doi, targetUrl):
  """
  Sets the target URL of an existing scheme-less DOI identifier (e.g.,
  "10.5060/foo").  No error checking is done on the inputs.
  """
  registerIdentifier(doi, targetUrl)

def _interpolate (template, *args):
  return template % tuple(xml.sax.saxutils.escape(a) for a in args)

_metadataTemplate = u"""<?xml version="1.0" encoding="UTF-8"?>
<resource xmlns="http://datacite.org/schema/kernel-2.1"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://datacite.org/schema/kernel-2.1
    http://schema.datacite.org/meta/kernel-2.1/metadata.xsd">
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
</resource>"""

def uploadMetadata (doi, metadata):
  """
  Uploads citation metadata for the resource identified by an existing
  scheme-less DOI identifier (e.g., "10.5060/foo") to DataCite.  This
  same function can be used to overwrite previously-uploaded metadata.
  'metadata' should be a dictionary that maps metadata element names
  (e.g., "Title") to values.  No error checking is done on the inputs.
  """
  creator = metadata.get("datacite.creator", "none supplied")
  title = metadata.get("datacite.title", "none supplied")
  publisher = metadata.get("datacite.publisher", "none supplied")
  date = metadata.get("datacite.publicationyear", "0000")
  if not re.match("\d{4}$", date): date = "0000"
  o = urllib2.build_opener(_HTTPErrorProcessor)
  r = urllib2.Request(_metadataUrl)
  # We manually supply the HTTP Basic authorization header to avoid
  # the doubling of the number of HTTP transactions caused by the
  # challenge/response model.
  r.add_header("Authorization", _auth)
  r.add_header("Content-Type", "application/xml; charset=UTF-8")
  r.add_data(_interpolate(_metadataTemplate, doi, creator, title, publisher,
    date).encode("UTF-8"))
  c = o.open(r)
  assert c.read() == "OK",\
   "unexpected return from DataCite store metadata operation"
  c.close()

def identifierExists (doi):
  # TBD
  return False

def ping ():
  """
  Tests the DataCite API, returning "up" or "down".
  """
  try:
    registerIdentifier("10.5072/cdl_status_check", "http://www.cdlib.org/")
  except Exception, e:
    return "down"
  else:
    return "up"
