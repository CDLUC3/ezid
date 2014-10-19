# =============================================================================
#
# EZID :: noid_nog_standalone.py
#
# Standalone version of noid_nog.py for use by offline tools.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2014, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import base64
import urllib2

class Minter (object):
  """
  A minter for a specific shoulder.
  """

  def __init__ (self, url, username, password):
    """
    Creates an interface to the noid nog minter at the supplied URL
    using the supplied credentials.
    """
    self.url = url
    self.username = username
    self.password = password

  def _addAuthorization (self, request):
    request.add_header("Authorization", "Basic " +\
      base64.b64encode(self.username + ":" + self.password))

  def mintIdentifier (self):
    """
    Mints and returns a scheme-less ARK identifier, e.g.,
    "13030/fk35717n0h".  Raises an exception on error.
    """
    r = urllib2.Request(self.url + "?mint%201")
    self._addAuthorization(r)
    c = None
    try:
      c = urllib2.urlopen(r)
      s = c.readlines()
    finally:
      if c: c.close()
    assert len(s) >= 2 and s[0].startswith("id:") and\
      s[-2] == "nog-status: 0\n",\
      "unexpected return from minter, output follows\n" + "".join(s)
    return s[0][3:].strip()
