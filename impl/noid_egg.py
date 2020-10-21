# =============================================================================
#
# EZID :: noid_egg.py
#
# Interface to the "egg" (binder) portion of noid.
#
# A note on encodings.  Identifiers and metadata elements (both names
# and values) are sent to noid in encoded form; see util.encode{3,4}.
# Metadata elements received from noid are UTF-8-encoded and utilize
# percent-encoding.  Though this received encoding does not exactly
# match the transmitted encoding, the decoding performed by
# util.decode is nevertheless compatible and so we use it.  (Consider
# a Python Unicode value u"Greg%Jan\xe9e".  This is sent as
# "Greg%25Jan%C3%A9e" but received back as "Greg%25Jan\xc3\xa9e",
# which, when percent- and UTF-8-decoded, yields the original value.)
#
# This module performs whitespace processing.  Leading and trailing
# whitespace is stripped from both element names and values.  Empty
# names are not allowed.  Setting an empty value causes the element to
# be deleted; as a consequence, empty values are never returned.
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
import re
import time
import urllib2

import config
import util

import logging
from log import stacklog

_LT = logging.getLogger("tracer")

_server = None
_authorization = None
_numAttempts = None
_reattemptDelay = None


def loadConfig():
    global _server, _authorization, _numAttempts, _reattemptDelay
    _server = config.get("binder.url")
    _authorization = "Basic " + base64.b64encode(
        config.get("binder.username") + ":" + config.get("binder.password")
    )
    _numAttempts = int(config.get("binder.num_attempts"))
    _reattemptDelay = int(config.get("binder.reattempt_delay"))


@stacklog
def _issue(method, operations):
    r = urllib2.Request(_server + "?-")
    r.get_method = lambda: method
    r.add_header("Authorization", _authorization)
    if len(operations) > 0:
        r.add_header("Content-Type", "text/plain")
        l = []
        for o in operations:
            # o = (identifier, operation [,element [, value]])
            s = ":hx%% %s.%s" % (util.encode4(o[0]), o[1])
            if len(o) > 2:
                s += " " + util.encode4(o[2])
            if len(o) > 3:
                s += " " + util.encode3(o[3])
            l.append(s)
        r.add_data("\n".join(l))
    for i in range(_numAttempts):
        c = None
        try:
            c = urllib2.urlopen(r)
            s = c.readlines()
        except:
            if i == _numAttempts - 1:
                raise
        else:
            break
        finally:
            if c:
                c.close()
        time.sleep(_reattemptDelay)
    return s


def _error(operation, s):
    return (
        "unexpected return from noid egg '%s' operation, " + "output follows\n%s"
    ) % (operation, "".join(s))


def identifierExists(identifier):
    """
  Returns true if an identifier (given in normalized, qualified form,
  e.g., "doi:10.1234/FOO") exists.  Raises an exception on error.
  """
    # The question of whether an identifier exists or not is
    # surprisingly elusive.  Noid will return information for any
    # identifier string, so we can't use that as a test.  Instead, we
    # test for the presence of metadata.  EZID populates a newly-created
    # identifier with multiple metadata fields.  (Noid adds its own
    # internal metadata fields, but only in response to EZID adding
    # fields.)  Note that the 'getElements' and 'deleteIdentifier'
    # functions below work to maintain the invariant property that
    # either an identifier has EZID metadata (along with noid-internal
    # metadata) or it has no metadata at all.
    s = _issue("GET", [(identifier, "fetch")])
    assert (
        len(s) >= 4
        and s[0].startswith("# id:")
        and s[-3].startswith("# elements bound under")
        and s[-2] == "egg-status: 0\n"
    ), _error("fetch", s)
    m = re.search(": (\d+)\n$", s[-3])
    assert m, _error("fetch", s)
    return m.group(1) != "0"


def setElements(identifier, d):
    """
  Binds metadata elements to an identifier (given in normalized,
  qualified form, e.g., "doi:10.1234/FOO").  The elements should be
  given in a dictionary that maps names to values.  Raises an
  exception on error.
  """
    batchSetElements([(identifier, d)])


def batchSetElements(batch):
    """
  Similar to 'setElements' above, but operates on multiple identifiers
  in one request.  'batch' should be a list of (identifier, name/value
  dictionary) tuples.
  """
    l = []
    for identifier, d in batch:
        for e, v in d.items():
            e = e.strip()
            assert len(e) > 0, "empty label"
            v = v.strip()
            if v == "":
                l.append((identifier, "rm", e))
            else:
                l.append((identifier, "set", e, v))
    s = _issue("POST", l)
    assert len(s) >= 2 and s[-2] == "egg-status: 0\n", _error("set/rm", s)


def getElements(identifier):
    """
  Returns all metadata elements (in the form of a dictionary) that are
  bound to an identifier (given in normalized, qualified form, e.g.,
  "doi:10.1234/FOO"), or None if the identifier doesn't exist.  Raises
  an exception on error.
  """
    # See the comment under 'identifierExists' above.
    s = _issue("GET", [(identifier, "fetch")])
    assert (
        len(s) >= 4
        and s[0].startswith("# id:")
        and s[-3].startswith("# elements bound under")
        and s[-2] == "egg-status: 0\n"
    ), _error("fetch", s)
    m = re.search(": (\d+)\n$", s[-3])
    assert m, _error("fetch", s)
    c = int(m.group(1))
    assert len(s) == c + 4, _error("fetch", s)
    if c == 0:
        return None
    else:
        d = {}
        for l in s[1 : len(s) - 3]:
            assert ":" in l, _error("fetch", s)
            if l.startswith("__") or l.startswith("_.e") or l.startswith("_,e"):
                continue
            e, v = l.split(":", 1)
            d[util.decode(e)] = util.decode(v.strip())
        # There had better be at least one non-noid-internal binding.
        assert len(d) > 0, _error("fetch", s)
        return d


def deleteIdentifier(identifier):
    """
  Deletes all metadata elements (including noid-internal elements)
  bound to an identifier (given in normalized, qualified form, e.g.,
  "doi:10.1234/FOO").  After calling this function, the identifier is
  deleted in the sense that identifierExists(identifier) will return
  False and getElements(identifier) will return None.  As far as noid
  is concerned, however, the identifier still exists and metadata
  elements can be re-bound to it in the future.  Raises an exception
  on error.
  """
    s = _issue("POST", [(identifier, "purge")])
    assert len(s) >= 2 and s[-2] == "egg-status: 0\n", _error("purge", s)
    # See the comment under 'identifierExists' above.
    assert not identifierExists(identifier), (
        "noid egg 'purge' operation on %s left remaining bindings" % identifier
    )


def batchDeleteIdentifier(batch):
    """
  Similar to 'deleteIdentifier' above, but deletes a list of
  identifiers in one request.
  """
    # The following code does not verify that all bindings have been
    # removed as 'deleteIdentifier' does above.  But that code is just a
    # guard against noid API changes, and having it in one place is
    # sufficient.
    s = _issue("POST", [(identifier, "purge") for identifier in batch])
    assert len(s) >= 2 and s[-2] == "egg-status: 0\n", _error("purge", s)


def ping():
    """
  Tests the server, returning "up" or "down".
  """
    try:
        s = _issue("GET", [])
        assert len(s) >= 2 and s[-2] == "egg-status: 0\n"
        return "up"
    except Exception:
        return "down"


_decodePattern = re.compile("\^([0-9a-fA-F][0-9a-fA-F])?")


def _decodeRewriter(m):
    assert len(m.group(0)) == 3, "circumflex decode error"
    return chr(int(m.group(0)[1:], 16))


def decodeRaw(s):
    """
  Decodes an identifier or metadata element name as stored internally
  in noid.  Raises AssertionError and UnicodeDecodeError.
  """
    return _decodePattern.sub(_decodeRewriter, s).decode("UTF-8")
