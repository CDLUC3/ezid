# =============================================================================
#
# EZID :: anvl.py
#
# Support for A Name-Value Language (ANVL) text formatting
# <http://wiki.ucop.edu/display/Curation/Anvl>.
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

class AnvlParseException (Exception):
  pass

_pattern1 = re.compile("[%:\r\n]")
_pattern2 = re.compile("[%\r\n]")
_pattern3 = re.compile("%([0-9a-fA-F][0-9a-fA-F])?")

def _encode (pattern, s):
  return pattern.sub(lambda c: "%%%02X" % ord(c.group(0)), s)

def _encodeLabel (s):
  return _encode(_pattern1, s)

def _encodeValue (s):
  return _encode(_pattern2, s)

def _decodeRewriter (m):
  if len(m.group(0)) == 3:
    return chr(int(m.group(0)[1:], 16))
  else:
    raise AnvlParseException, "percent-decode error"

def _decode (s):
  return _pattern3.sub(_decodeRewriter, s)

def formatPair (label, value):
  """
  Formats a label and value into an ANVL element.
  """
  return "%s: %s\n" % (_encodeLabel(label), _encodeValue(value))

def format (d):
  """
  Formats a dictionary into an ANVL string.  Labels and values are
  suitably percent-encoded.
  """
  return "".join(formatPair(k, v) for k, v in d.items())

def parse (s):
  """
  Parses an ANVL string and returns a dictionary.  Labels and values
  are percent-decoded.  Raises AnvlParseException (defined in this
  module).
  """
  d = {}
  k = None
  for l in s.splitlines():
    if len(l) == 0:
      k = None
    elif l[0] == "#":
      pass
    elif l[0].isspace():
      if k == None:
        raise AnvlParseException, "no previous label for continuation line"
      ll = _decode(l).strip()
      if ll != "":
        if d[k] == "":
          d[k] = ll
        else:
          d[k] += " " + ll
    else:
      if ":" not in l: raise AnvlParseException, "no colon in line"
      k, v = [_decode(w).strip() for w in l.split(":", 1)]
      if len(k) == 0: raise AnvlParseException, "empty label"
      d[k] = v
  return d
