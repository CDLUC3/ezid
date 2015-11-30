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

import calendar
import datetime
import lxml.etree
import re
import sys
import zlib

maxIdentifierLength = 255

_doiPattern = re.compile("10\.[1-9]\d{3,4}/[!\"$->@-~]+$")

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
  # ASCII characters except (#) and (?).  (Hash marks may be confused
  # with fragment identifiers.  Question marks are excluded to
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
  if len(doi) > maxIdentifierLength-4: return None
  return doi.upper()

_arkPattern1 = re.compile("((?:\d{5}(?:\d{4})?|[b-k]\d{4})/)([!-~]+)$")
_arkPattern2 = re.compile("\./|/\.")
_arkPattern3 = re.compile("([./])[./]+")
_arkPattern4 = re.compile("^[./]|[./]$")
_arkPattern5 = re.compile("%[0-9a-fA-F][0-9a-fA-F]|.")
_arkPattern6 = re.compile("[0-9a-zA-Z=*+@_$~]")
_arkPattern7 = re.compile("[0-9a-zA-Z=*+@_$~./]")

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
  # restrictive: we allow all graphic ASCII characters; our length
  # upper bound is more permissive; we allow the first character to be
  # alphabetic; and we allow variant paths to be intermixed with
  # component paths.  All these relaxations are intended to support
  # shadow ARKs and relatively direct transformation of DOIs into
  # shadow ARKs.  The normalizations performed here follow the rules
  # given in the specification except that we don't re-order variant
  # paths, which would conflict with transformation of DOIs into
  # shadow ARKs (since order of period-delimited components in DOIs is
  # significant).  Also, hash marks (#) are percent encoded to avoid
  # confusion with their interpretation as fragment identifiers.
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
  if len(p)+len(s) > maxIdentifierLength-5: return None
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

def validateIdentifier (identifier):
  """
  If the supplied string is any type of qualified, syntactically valid
  identifier, returns the canonical form of the identifier.
  Otherwise, returns None.
  """
  if identifier.startswith("ark:/"):
    s = validateArk(identifier[5:])
    if s != None:
      return "ark:/" + s
    else:
      return None
  elif identifier.startswith("doi:"):
    s = validateDoi(identifier[4:])
    if s != None:
      return "doi:" + s
    else:
      return None
  elif identifier.startswith("urn:uuid:"):
    s = validateUrnUuid(identifier[9:])
    if s != None:
      return "urn:uuid:" + s
    else:
      return None
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

_hexDigits = "0123456789ABCDEFabcdef"
_hexMapping = dict((a+b, chr(int(a+b, 16))) for a in _hexDigits\
  for b in _hexDigits)

def decode (s):
  """
  Decodes a string that was encoded by encode{1,2,3,4}.  Raises
  PercentDecodeError (defined in this module) and UnicodeDecodeError.
  """
  l = s.split("%")
  r = [l[0]]
  for p in l[1:]:
    try:
      r.append(_hexMapping[p[:2]])
      r.append(p[2:])
    except KeyError:
      raise PercentDecodeError()
  return "".join(r).decode("UTF-8")

def toExchange (metadata, identifier=None):
  """
  Returns an exchange representation of a metadata dictionary, which
  is a string of the format "label value label value ..." in which
  labels and values are percent-encoded via encode{3,4} above, and are
  separated by single spaces.  Labels and values are stripped before
  being encoded; empty labels are not permitted and labels with empty
  values are discarded.  If 'identifier' is not None, it is inserted
  as the first token in the string; it is not encoded.
  """
  l = []
  if identifier != None:
    # We're assuming here that the identifier contains no spaces or
    # newlines, but we don't check that.
    l.append(identifier)
  for k, v in metadata.items():
    k = k.strip()
    assert len(k) > 0, "empty label"
    v = v.strip()
    if len(v) > 0:
      l.append(encode4(k))
      l.append(encode3(v))
  return " ".join(l)

def fromExchange (line, identifierEmbedded=False):
  """
  Reconstitutes a metadata dictionary from an exchange representation.
  If 'identifierEmbedded' is True, the first token is assumed to be an
  identifier, and the return is a tuple (identifier, dictionary).
  Otherwise, the return is simply a dictionary.  N.B.: this function
  only partially checks the input.
  """
  if len(line) > 0 and line[-1] == "\n": line = line[:-1]
  if len(line) == 0:
    assert not identifierEmbedded, "wrong number of tokens"
    return {}
  v = line.split(" ")
  if identifierEmbedded:
    assert len(v)%2 == 1, "wrong number of tokens"
    assert len(v[0]) > 0, "empty token"
    identifier = v[0]
    start = 1
  else:
    assert len(v)%2 == 0, "wrong number of tokens"
    start = 0
  d = {}
  for i in range(start, len(v), 2):
    assert len(v[i]) > 0 and len(v[i+1]) > 0, "empty token"
    d[decode(v[i])] = decode(v[i+1])
  if identifierEmbedded:
    return identifier, d
  else:
    return d

def blobify (metadata):
  """
  Converts a metadata dictionary to a binary, compressed string, or
  "blob."  Labels and values are stripped; labels with empty values
  are discarded.
  """
  return zlib.compress(toExchange(metadata))

def deblobify (blob, decompressOnly=False):
  """
  Converts a blob back to a metadata dictionary.  If 'decompressOnly'
  is True, the metadata is returned in exchange representation form.
  """
  v = zlib.decompress(blob)
  if decompressOnly:
    return v
  else:
    return fromExchange(v)

def oneLine (s):
  """
  Replaces newlines in a string with spaces.
  """
  return re.sub("\s", " ", s)

def formatException (exception):
  """
  Formats an exception into a single-line string.
  """
  s = oneLine(str(exception)).strip()
  if len(s) > 0: s = ": " + s
  return type(exception).__name__ + s

# The following definitions are taken from the XML 1.1 specification.
# The characters we consider illegal include restricted and
# discouraged characters, but compatibility characters are still
# allowed.  Python's implementation of Unicode is significant here.
# If Unicode is stored as UCS-2 (which is the case on every platform
# encountered to date), then it's not possible to use regular
# expressions to check for characters higher than 0xFFFF, and we
# necessarily allow surrogate characters (though we don't check that
# surrogates come in pairs and are properly ordered, nor do we check
# for discouraged characters higher than 0xFFFF).  If Python stores
# Unicode as UCS-4, then surrogate characters are not allowed, and we
# check for discouraged characters in all planes.

_illegalUnichrs = [(0x00, 0x08), (0x0B, 0x0C), (0x0E, 0x1F), (0x7F, 0x84),
  (0x86, 0x9F), (0xFDD0, 0xFDDF), (0xFFFE, 0xFFFF)]
if sys.maxunicode >= 0x10000:
  _illegalUnichrs.extend([(0xD800, 0xDFFF), (0x1FFFE, 0x1FFFF),
    (0x2FFFE, 0x2FFFF), (0x3FFFE, 0x3FFFF), (0x4FFFE, 0x4FFFF),
    (0x5FFFE, 0x5FFFF), (0x6FFFE, 0x6FFFF), (0x7FFFE, 0x7FFFF),
    (0x8FFFE, 0x8FFFF), (0x9FFFE, 0x9FFFF), (0xAFFFE, 0xAFFFF),
    (0xBFFFE, 0xBFFFF), (0xCFFFE, 0xCFFFF), (0xDFFFE, 0xDFFFF),
    (0xEFFFE, 0xEFFFF), (0xFFFFE, 0xFFFFF), (0x10FFFE, 0x10FFFF)])

_illegalUnichrsRE = re.compile(u"[%s]" % u"".join("%s-%s" % (unichr(low),
  unichr(high)) for low, high in _illegalUnichrs))

def validateXmlSafeCharset (s):
  """
  Returns true if the given Unicode string contains only characters
  that are accepted by XML 1.1.
  """
  return _illegalUnichrsRE.search(s) == None

def sanitizeXmlSafeCharset (s):
  """
  Returns a copy of the given Unicode string in which characters not
  accepted by XML 1.1 have been replaced with spaces.
  """
  return _illegalUnichrsRE.sub(" ", s)

if sys.maxunicode >= 0x10000:
  _illegalUnichrsPlusSuppPlanes = _illegalUnichrs + [(0x10000, 0x10FFFF)]
else:
  _illegalUnichrsPlusSuppPlanes = _illegalUnichrs + [(0xD800, 0xDFFF)]

_illegalUnichrsPlusSuppPlanesRE =\
  re.compile(u"[%s]" % u"".join("%s-%s" % (unichr(low),
  unichr(high)) for low, high in _illegalUnichrsPlusSuppPlanes))

def validateXmlSafeCharsetBmpOnly (s):
  """
  Returns true if the given Unicode string contains only characters
  that are accepted by XML 1.1 and that are in the Basic Multilingual
  Plane.
  """
  return _illegalUnichrsPlusSuppPlanesRE.search(s) == None

xmlDeclarationRE = re.compile("<\?xml\s+version\s*=\s*(['\"])([-\w.:]+)\\1" +\
  "(\s+encoding\s*=\s*(['\"])([a-zA-Z][-\w.]*)\\4)?" +\
  "(\s+standalone\s*=\s*(['\"])(yes|no)\\7)?\s*\?>\s*")

def removeXmlEncodingDeclaration (document):
  """
  Removes the encoding declaration from an XML document if present.
  """
  m = xmlDeclarationRE.match(document)
  if m and m.group(3) != None:
    return document[:m.start(3)] + document[m.end(3):]
  else:
    return document

def removeXmlDeclaration (document):
  """
  Removes the entire XML declaration from an XML document if present.
  """
  m = xmlDeclarationRE.match(document)
  if m:
    return document[len(m.group(0)):]
  else:
    return document

def insertXmlEncodingDeclaration (document):
  """
  Inserts a UTF-8 encoding declaration in an XML document if it lacks
  one.  'document' should be an unencoded string and the return is
  likewise an unencoded string.  (Note that, due to the discrepancy
  between the encoding declaration and the encoding of the returned
  string, to be parsed again by lxml, the encoding declaration will
  need to be removed.)
  """
  m = xmlDeclarationRE.match(document)
  if m:
    if m.group(3) == None:
      return document[:m.end(2)+1] + " encoding=\"UTF-8\"" +\
        document[m.end(2)+1:]
    else:
      return document
  else:
    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" + document

def parseXmlString (document):
  """
  Parses an XML document from a string, returning a root element node.
  If a Unicode string is supplied, any encoding declaration in the
  document is discarded and ignored; otherwise, if an encoding
  declaration is present, the parser treats the string as a binary
  stream and decodes it per the declaration.
  """
  if type(document) is str:
    return lxml.etree.XML(document)
  elif type(document) is unicode:
    return lxml.etree.XML(removeXmlEncodingDeclaration(document))
  else:
    assert False, "unhandled case"

_extractTransform = None
_extractTransformSource = """<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

<xsl:output method="text" encoding="UTF-8"/>
<xsl:strip-space elements="*"/>

<xsl:template match="*">
  <xsl:for-each select="@*">
    <xsl:if test="not(local-name()='schemaLocation')">
      <xsl:if test="normalize-space(.) != ''">
        <xsl:value-of select="normalize-space(.)"/>
        <xsl:text> ; </xsl:text>
      </xsl:if>
    </xsl:if>
  </xsl:for-each>
  <xsl:apply-templates/>
</xsl:template>

<xsl:template match="text()">
  <xsl:value-of select="normalize-space(.)"/>
  <xsl:text> ; </xsl:text>
</xsl:template>

</xsl:stylesheet>"""

def extractXmlContent (document):
  """
  Extracts all content from an XML document (all attribute values, all
  textual element content) and returns it as a single Unicode string
  in which individual fragments are separated by " ; ".  Whitespace is
  normalized throughout per XPath.  The input document may be a string
  or an already-parsed document tree.
  """
  global _extractTransform
  if _extractTransform == None:
    _extractTransform = lxml.etree.XSLT(lxml.etree.XML(
      _extractTransformSource))
  if isinstance(document, basestring): document = parseXmlString(document)
  return unicode(_extractTransform(document)).strip()[:-2]

_datespecRE = re.compile("(\d{4})(?:-(\d\d)(?:-(\d\d))?)?$")

def dateToLowerTimestamp (date):
  """
  Converts a string date of the form YYYY, YYYY-MM, or YYYY-MM-DD to a
  Unix timestamp, or returns None if the date is invalid.  The
  returned timestamp is the first (earliest) second within the
  specified time period.  Note that the timestamp may be negative or
  otherwise out of the normal range for Unix timestamps.
  """
  rm = _datespecRE.match(date)
  if not rm or date[-1] == "\n": return None
  y = int(rm.group(1))
  m = int(rm.group(2)) if rm.group(2) != None else 1
  d = int(rm.group(3)) if rm.group(3) != None else 1
  try:
    return calendar.timegm(datetime.date(y, m, d).timetuple())
  except ValueError:
    return None

def dateToUpperTimestamp (date):
  """
  Converts a string date of the form YYYY, YYYY-MM, or YYYY-MM-DD to a
  Unix timestamp, or returns None if the date is invalid.  The
  returned timestamp is the last (latest) second within the specified
  time period.  Note that the timestamp may be negative or otherwise
  out of the normal range for Unix timestamps.
  """
  # Overflow and edge cases.
  if date in ["9999", "9999-12", "9999-12-31"]:
    return calendar.timegm(
      datetime.datetime(9999, 12, 31, 23, 59, 59).timetuple())
  elif date == "0000":
    return None
  rm = _datespecRE.match(date)
  if not rm or date[-1] == "\n": return None
  try:
    y = int(rm.group(1))
    if rm.group(2) == None:
      date = datetime.date(y+1, 1, 1)
    else:
      m = int(rm.group(2))
      if rm.group(3) == None:
        date = (datetime.date(y, m, 1) +\
          datetime.timedelta(days=31)).replace(day=1)
      else:
        date = datetime.date(y, m, int(rm.group(3))) +\
          datetime.timedelta(days=1)
    return calendar.timegm(date.timetuple()) - 1
  except ValueError:
    return None
