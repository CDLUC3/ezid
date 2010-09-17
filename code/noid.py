# =============================================================================
#
# EZID :: noid.py
#
# Interface to noid <http://wiki.ucop.edu/display/Curation/NOID>.
# Because EZID interacts with multiple noid servers, the interface is
# expressed as a class.
#
# Note that metadata elements (both names and values) are stored in
# noid in encoded form; see util.encode{3,4} and util.decode.
#
# This module assumes that identifiers have already been normalized
# per util.validateArk.  ARK normalization provides its own encoding;
# this module does not further encode identifiers.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2010, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import urllib2

import util

class Noid (object):

  def __init__ (self, server):
    """
    Creates an interface to the noid server at the supplied base URL.
    """
    self.server = server

  def _command (self, *args):
    l = []
    for a in args:
      if type(a) is list: # [encoding, value]
        if len(a[1]) == 0:
          l.append("''")
        else:
          if a[0] == 0:
            l.append(a[1])
          elif a[0] == 4:
            l.append(util.encode4(a[1]))
          else:
            l.append(util.encode3(a[1]))
      else:
        if len(a) == 0:
          l.append("''")
        else:
          l.append(util.encode3(a))
    return " ".join(l)

  def _issue (self, commands):
    r = urllib2.Request(self.server + "?-")
    r.add_header("Content-Type", "text/plain")
    r.add_data(commands)
    c = urllib2.urlopen(r)
    s = c.readlines()
    c.close()
    return s

  def identifierExists (self, identifier):
    """
    Returns true if a scheme-less ARK identifier (e.g., "13030/foo")
    exists.  The identifier is assumed to be in canonical form.
    """
    # The question of whether an identifier exists or not is
    # surprisingly elusive.  Noid will return information for any
    # identifier string, so we can't use that as a test.  Minted
    # identifiers have holds placed on them, but per the noid
    # specification, a hold is really a kind of reservation, not an
    # indicator of existence.  There's a circulation status line, but
    # it gets filled out only if the identifier is minted by noid, not
    # if the identifier comes into existence by virtue of metadata
    # being bound to it.  That leaves presence of metadata as the
    # test.  A newly-minted identifier has no metadata, but
    # identifiers minted by EZID will always have some.  Thus this
    # test if imperfect, but it's the least imperfect test.
    s = self._issue(self._command("fetch", [0, identifier]))
    assert len(s) >= 3 and s[0].startswith("id:") and\
      s[1].startswith("Circ:"), "unexpected return from noid 'fetch' command"
    return not s[2].startswith("note: no elements bound under")

  def mintIdentifier (self):
    """
    Mints and returns a scheme-less ARK identifier, e.g.,
    "13030/fk35717n0h".
    """
    s = self._issue(self._command("mint", "1"))
    assert len(s) >= 1 and s[0].startswith("id:"),\
      "unexpected return from noid 'mint' command"
    return s[0][3:].strip()

  def holdIdentifier (self, identifier):
    """
    Places a hold on an identifier.  The identifier is assumed to be
    in canonical form.
    """
    s = self._issue(self._command("hold", "set", [0, identifier]))
    assert len(s) >= 1 and s[0].startswith("ok: 1 hold placed"),\
      "unexpected return from noid 'hold set' command"

  def setElements (self, identifier, d):
    """
    Binds metadata elements to a scheme-less ARK identifier, e.g.,
    "13030/foo".  The identifier is assumed to be in canonical form.
    The elements should be given in a dictionary that maps names to
    values.  Note that an identifier must have a hold placed on it
    before any metadata can be bound.
    """
    s = self._issue("\n".join(self._command("bind", "set", [0, identifier],
      [4, e], v) for e, v in d.items()))
    for i in range(len(d)):
      assert len(s) >= i*5+4 and s[i*5+3].startswith("Status:  ok"),\
        "unexpected return from noid 'bind set' command"

  def getElements (self, identifier):
    """
    Returns all metadata elements (in the form of a dictionary) that
    are bound to a scheme-less ARK identifier, e.g., "13030/foo".  The
    identifier is assumed to be in canonical form.
    """
    s = self._issue(self._command("fetch", [0, identifier]))
    assert len(s) >= 3 and s[0].startswith("id:") and\
      s[1].startswith("Circ:"), "unexpected return from noid 'fetch' command"
    if s[2].startswith("note: no elements bound under"):
      return {}
    else:
      d = {}
      for l in s[2:]:
        if ":" in l:
          e, v = l.split(":", 1)
          d[util.decode(e)] = util.decode(v.strip())
      return d
