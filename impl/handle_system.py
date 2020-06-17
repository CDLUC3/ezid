# =============================================================================
#
# EZID :: handle_system.py
#
# Handle System utilities.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2017, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import urllib
import urllib2

class _RedirectCatcher (urllib2.HTTPRedirectHandler):
  def redirect_request (self, req, fp, code, msg, headers, newurl):
    raise urllib2.HTTPError(req.get_full_url(), code, "redirect", headers, fp)

def getRedirect (doi):
  """
  Returns the target URL for an identifier as recorded with the global
  DOI resolver (doi.org), or None if the identifier isn't found.
  'doi' should be a scheme-less DOI identifier, e.g., "10.1234/FOO".
  Raises an exception on other errors.
  """
  o = urllib2.build_opener(_RedirectCatcher())
  r = urllib2.Request("https://doi.org/" + urllib.quote(doi, ":/"))
  c = None
  try:
    c = o.open(r)
    c.read()
  except urllib2.HTTPError, e:
    if e.code in [301, 302, 303, 307]:
      assert "location" in e.headers, "redirect has no Location header"
      return e.headers["location"]
    elif e.code == 404:
      return None
    else:
      raise
  else:
    assert False, "expecting a redirect from doi.org"
  finally:
    if c: c.close()
