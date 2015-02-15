# =============================================================================
#
# EZID :: util.py
#
# Utility functions.
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

maximumIdentifierLength = 256

_doiPattern = re.compile("10\.[1-9]\d{3,4}/[!->@-~]+$")
def validateDoi (doi):
  """
  If the supplied string (e.g., "10.5060/foo") is a syntactically
  valid scheme-less DOI identifier, returns the canonical form of the
  identifier (namely, uppercased).  Otherwise, returns None.
  """
  # Our validation is generally more restrictive than what is allowed
  # by the DOI Handbook <doi:10.1000/186>, though not in any way that
  # should be limiting in practice.  The Handbook allows virtually any
  # prefix; we allow only 4 or 5 digits.  The Handbook allows all
  # printable Unicode characters in the suffix; we allow all graphic
  # ASCII characters except (?).  (Question marks are excluded to
  # eliminate any possible confusion over whether a dx.doi.org-style
  # "urlappend" argument is part of the identifier or not; our
  # position is that it is not.)  But our validation is also more
  # permissive in one aspect: we don't check that the suffix does
  # *not* match "./.*", which the Handbook claims is reserved (only in
  # the appendix, not in the main text, though).
  # Update: we disallow adjacent slashes and trailing slashes because
  # such constructs conflict with the direct embedding of identifiers
  # in URLs (as is done in the EZID API and the dx.doi.org resolver).
  if not _doiPattern.match(doi) or doi[-1] == "\n": return None
  if "//" in doi or doi.endswith("/"): return None
  # We should probably test the length of the shadow ARK as well (it
  # may be longer than the DOI due to extra percent encoding), but
  # don't at present.
  if len(doi) > maximumIdentifierLength-4: return None
  return doi.upper()

_arkPattern1 = re.compile("((?:\d{5}(?:\d{4})?|[b-k]\d{4})/)([!-~]+)$")
_arkPattern2 = re.compile("\./|/\.")
_arkPattern3 = re.compile("([./])[./]+")
_arkPattern4 = re.compile("^[./]|[./]$")
_arkPattern5 = re.compile("%[0-9a-fA-F][0-9a-fA-F]|.")
_arkPattern6 = re.compile("[0-9a-zA-Z=#*+@_$~]")
_arkPattern7 = re.compile("[0-9a-zA-Z=#*+@_$~./]")

def _normalizeArkPercentEncoding (m):
  s = m.group(0)
  if len(s) == 3:
    c = chr(int(s[1:], 16))
    if _arkPattern6.match(c):
      return c
    else:
      return s.lower()
  else:
    assert s != "%", "malformed percent-encoding"
    if _arkPattern7.match(s):
      return s
    else:
      return "%%%02x" % ord(s)

def validateArk (ark):
  """
  If the supplied string (e.g., "13030/foo") is a syntactically valid
  scheme-less ARK identifier, returns the canonical form of the
  identifier.  Otherwise, returns None.
  """
  # Our validation diverges from the ARK specification
  # <http://wiki.ucop.edu/display/Curation/ARK> in that it is not as
  # restrictive: we allow all graphic ASCII characters; we place no
  # limit on length; we allow the first character to be alphabetic;
  # and we allow variant paths to be intermixed with component paths.
  # All these relaxations are intended to support shadow ARKs and
  # relatively direct transformation of DOIs into shadow ARKs.  The
  # normalizations performed here follow the rules given in the
  # specification except that we don't re-order variant paths, which
  # would conflict with transformation of DOIs into shadow ARKs (since
  # order of period-delimited components in DOIs is significant).
  m = _arkPattern1.match(ark)
  if not m or ark[-1] == "\n": return None
  p = m.group(1)
  s = m.group(2)
  # Hyphens are insignificant.
  s = s.replace("-", "")
  # Dissimilar adjacent structural characters are not allowed.
  if _arkPattern2.search(s): return None
  # Consolidate adjacent structural characters.
  s = _arkPattern3.sub("\\1", s)
  # Eliminate leading and trailing structural characters.
  s = _arkPattern4.sub("", s)
  if len(s) == 0: return None
  # Normalize percent-encodings.
  try:
    s = _arkPattern5.sub(_normalizeArkPercentEncoding, s)
  except AssertionError:
    return None
  if len(p)+len(s) > maximumIdentifierLength-5: return None
  return p+s

_urnUuidPattern = re.compile("[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$",
  re.I)

def validateUrnUuid (urn):
  """
  If the supplied string (e.g.,
  "f81d4fae-7dec-11d0-a765-00a0c91e6bf6") is a syntactically valid
  scheme-less UUID URN identifier as defined by RFC 4122
  <http://www.ietf.org/rfc/rfc4122.txt>, returns the canonical form of
  the identifier (namely, lowercased).  Otherwise, returns None.
  """
  if _urnUuidPattern.match(urn) and urn[-1] != "\n":
    return urn.lower()
  else:
    return None

def _percentEncodeCdr (m):
  s = m.group(0)
  return s[0] + "".join("%%%02x" % ord(c) for c in s[1:])

def doi2shadow (doi):
  """
  Given a scheme-less DOI identifier (e.g., "10.5060/FOO"), returns
  the corresponding scheme-less shadow ARK identifier (e.g.,
  "b5060/foo").  The returned identifier is in canonical form.  Note
  that the conversion is *not* in general reversible by shadow2doi.
  """
  # The conversion of DOIs to ARKs is a little tricky because ARKs
  # place semantics on certain characters in suffixes while DOIs do
  # not, and because ARKs use a restricted character set.  Our
  # conversion here is essentially direct mapping, on the assumption
  # that DOI identifiers will tend to more or less follow ARK
  # practices anyway.  Character conversion is handled by using
  # percent-encoding as specified in ARK normalization rules, but note
  # that we escape percent signs here because in DOIs percent signs do
  # *not* signify percent-encoding.  In addition, DOIs are lowercased
  # to match ARKs minted by noid, which are always lowercase (that is,
  # minted DOIs are formed from minted ARKs; to preserve the
  # programmatic conversion of DOIs to shadow ARKs for all DOIs, the
  # mapping to lowercase must be uniform).  It is possible for the
  # conversion to fail, but this should occur only in pathological
  # cases.
  # Update: to prevent different DOIs from mapping to the same shadow
  # ARK, we percent-encode characters (and only those characters) that
  # would otherwise be removed by the ARK normalization process.
  if doi[7] == "/":
    i = 8
    p = "b" + doi[3:i]
  else:
    i = 9
    p = chr(ord("c")+ord(doi[3])-ord("1")) + doi[4:i]
  s = doi[i:].replace("%", "%25").replace("-", "%2d").lower()
  s = _arkPattern4.sub(lambda c: "%%%02x" % ord(c.group(0)), s)
  s = _arkPattern3.sub(_percentEncodeCdr, s)
  a = validateArk(p + s)
  assert a != None, "shadow ARK failed validation"
  return a

def shadow2doi (ark):
  """
  Given a scheme-less shadow ARK identifier (e.g., "b5060/foo"),
  returns the corresponding scheme-less DOI identifier
  (e.g. "10.5060/FOO").  The returned identifier is in canonical form.
  This function is intended to be used for noid-minted ARK identifiers
  only; it is not in general the inverse of doi2shadow.
  """
  if ark[0] == "b":
    doi = "10." + ark[1:]
  else:
    doi = "10." + chr(ord("1")+ord(ark[0])-ord("c")) + ark[1:]
  return doi.upper()

_urnUuidShadowArkPrefix = "97720/"
def urnUuid2shadow (urn):
  """
  Given a scheme-less UUID URN identifier (e.g.,
  "f81d4fae-7dec-11d0-a765-00a0c91e6bf6"), returns the corresponding
  scheme-less shadow ARK identifier (e.g.,
  "97720/f81d4fae7dec11d0a76500a0c91e6bf6").  The URN is assumed to be
  in canonical form; the returned identifier is in canonical form.
  """
  return _urnUuidShadowArkPrefix + urn.replace("-", "")

def _encode (pattern, s):
  return pattern.sub(lambda c: "%%%02X" % ord(c.group(0)), s.encode("UTF-8"))

_pattern1 = re.compile("%|[^ -~]")
def encode1 (s):
  """
  UTF-8 encodes a Unicode string, then percent-encodes all non-graphic
  ASCII characters except space.  This form of encoding is used for
  log file exception strings.
  """
  return _encode(_pattern1, s)

_pattern2 = re.compile("%|[^!-~]")
def encode2 (s):
  """
  Like encode1, but percent-encodes spaces as well.  This form of
  encoding is used for log file record fields other than exception
  strings.
  """
  return _encode(_pattern2, s)

_pattern3 = re.compile("[%'\"\\\\&@|;()[\\]=]|[^!-~]")
def encode3 (s):
  """
  Like encode2, but percent-encodes ('), ("), (\), (&), (@), (|), (;)
  ((), ()), ([), (]), and (=) as well.  This form of encoding is used
  for noid element values.
  """
  return _encode(_pattern3, s)

_pattern4 = re.compile("[%'\"\\\\&@|;()[\\]=:<]|[^!-~]")
def encode4 (s):
  """
  Like encode3, but percent-encodes (:) and (<) as well.  This form of
  encoding is used for noid identifiers and noid element names.
  """
  return _encode(_pattern4, s)

class PercentDecodeError (Exception):
  pass

_decodePattern = re.compile("%([0-9a-fA-F][0-9a-fA-F])?")

def _decodeRewriter (m):
  if len(m.group(0)) == 3:
    return chr(int(m.group(0)[1:], 16))
  else:
    raise PercentDecodeError

def decode (s):
  """
  Decodes a string that was encoded by encode{1,2,3,4}.  Raises
  PercentDecodeError (defined in this module) and UnicodeDecodeError.
  """
  return _decodePattern.sub(_decodeRewriter, s).decode("UTF-8")
