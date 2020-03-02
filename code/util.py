# =============================================================================
#
# EZID :: util.py
#
# Utility functions.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#   Rushiraj Nenuji <rnenuji@ucop.edu>
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
import time
import xml.sax.saxutils
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

_arkPattern1 = re.compile("((?:\d{5}(?:\d{4})?|[bcdfghjkmnpqrstvwxz]\d{4})/)([!-~]+)$")
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

_uuidPattern = re.compile("[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$", re.I)

def validateUuid (id):
  """
  If the supplied string (e.g.,
  "f81d4fae-7dec-11d0-a765-00a0c91e6bf6") is a syntactically valid
  scheme-less UUID identifier as defined by RFC 4122
  <http://www.ietf.org/rfc/rfc4122.txt>, returns the canonical form of
  the identifier (namely, lowercased).  Otherwise, returns None.
  """
  if _uuidPattern.match(id) and id[-1] != "\n":
    return id.lower()
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
  elif identifier.startswith("uuid:"):
    s = validateUuid(identifier[5:])
    if s != None:
      return "uuid:" + s
    else:
      return None
  else:
    return None

def validateShoulder (shoulder):
  """
  Returns True if the supplied string is a valid shoulder, which is to
  say, if the string is a certain allowable prefix of a qualified,
  syntactically valid identifier.
  """
  # Strategy: a shoulder is valid if adding a single character yields
  # a valid identifier.
  if shoulder.startswith("ark:/"):
    id = shoulder[5:] + "x"
    return validateArk(id) == id
  elif shoulder.startswith("doi:"):
    id = shoulder[4:] + "X"
    return validateDoi(id) == id
  elif shoulder == "uuid:":
    return True
  else:
    return False

def inferredShoulder (identifier):
  """
  Given a normalized, qualified identifier (e.g., "ark:/12345/xy7qz"),
  infers and returns the identifier's shoulder (e.g.,
  "ark:/12345/xy").  This is typically the identifier up to the first
  two characters following the NAAN- or prefix-separating slash.
  """
  if identifier.startswith("ark:/"):
    return re.match("ark:/(\d{5}(\d{4})?|[b-k]\d{4})/[0-9a-zA-Z]{0,2}",
      identifier).group(0)
  elif identifier.startswith("doi:"):
    return re.match("doi:10\.[1-9]\d{3,4}/[0-9A-Z]{0,2}", identifier).group(0)
  else:
    return identifier.split(":")[0] + ":"

datacenterSymbolRE = re.compile(
  "^([A-Z][-A-Z0-9]{0,6}[A-Z0-9])\.([A-Z][-A-Z0-9]{0,6}[A-Z0-9])$", re.I)
maxDatacenterSymbolLength = 17

def validateDatacenter (symbol):
  """
  If the supplied string (e.g., "CDL.BUL") is a valid DataCite
  datacenter symbol, returns the canonical form of the symbol (namely,
  uppercased).  Otherwise, returns None.
  """
  if datacenterSymbolRE.match(symbol) and symbol[-1] != "\n":
    return symbol.upper()
  else:
    return None

def _percentEncodeCdr (m):
  s = m.group(0)
  return s[0] + "".join("%%%02x" % ord(c) for c in s[1:])

def doi2shadow (doi):
  """
  Given a scheme-less DOI identifier (e.g., "10.5060/FOO"), returns
  the corresponding scheme-less shadow ARK identifier (e.g.,
  "b5060/foo").  The returned identifier is in canonical form.
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
  beta_numeric_char = "bcdfghjkmnpqrstvwxz"
  doi_prefix = doi.split("/")[0]
  i = len(doi_prefix) + 1
  if doi[7] == "/":
    p = "b" + doi[3:i]
  else:
    if i == 9:
      p = beta_numeric_char[(ord(doi[3])-ord("0"))] + doi[4:i]
    elif i == 10:
      p = beta_numeric_char[((ord(doi[3]) - ord("0")) * 10) + (ord(doi[4]) - ord("0"))] + doi[5:i]
  s = doi[i:].replace("%", "%25").replace("-", "%2d").lower()
  s = _arkPattern4.sub(lambda c: "%%%02x" % ord(c.group(0)), s)
  s = _arkPattern3.sub(_percentEncodeCdr, s)
  a = validateArk(p + s)
  assert a != None, "shadow ARK failed validation"
  return a

_hexDecodePattern = re.compile("%([0-9a-fA-F][0-9a-fA-F])")

def shadow2doi (ark):
  """
  Given a scheme-less shadow ARK identifier for a DOI (e.g.,
  "b5060/foo"), returns the corresponding scheme-less DOI identifier
  (e.g., "10.5060/FOO").  The returned identifier is in canonical
  form.
  """
  beta_numeric_char = "bcdfghjkmnpqrstvwxz"
  if ark[0] == "b":
    doi = "10." + ark[1:]
  else:
    try:
      if beta_numeric_char.find(ark[0]) > -1:
        doi = "10." + str(beta_numeric_char.find(ark[0])) + ark[1:]
      else:
        raise Exception("Not a valid ark") 
    except:
      print "Sorry, an error occured while converting shadow 2 doi"
  return _hexDecodePattern.sub(lambda c: chr(int(c.group(1), 16)), doi).upper()

_shadowedDoiPattern = re.compile("ark:/[bcdfghjkmnpqrstvwxz]") # see _arkPattern1 above

def normalizeIdentifier (identifier):
  """
  Similar to 'validateIdentifier': if the supplied string is any type
  of qualified, syntactically valid identifier, returns the canonical
  form of the identifier.  However, if the identifier is a shadow ARK,
  this function instead returns (the canonical form of) the shadowed
  identifier.  On any kind of error, returns None.
  """
  id = validateIdentifier(identifier)
  if id == None: return None
  if id.startswith("ark:/"):
    # The reverse shadow function doesn't check that the supplied
    # identifier is indeed a valid shadow ARK, so we check that the
    # returned identifier is valid and produces the same shadow ARK.
    if _shadowedDoiPattern.match(id):
      doi = shadow2doi(id[5:])
      if validateDoi(doi) != None and doi2shadow(doi) == id[5:]:
        return "doi:" + doi
      else:
        return None
    else:
      return id
  else:
    return id

def explodePrefixes (identifier):
  """
  Given a normalized, qualified identifier (e.g., "ark:/12345/x/yz"),
  returns a list of all prefixes of the identifier that are
  syntactically valid identifiers (e.g., ["ark:/12345/x",
  "ark:/12345/x/y", "ark:/12345/x/yz"]).
  """
  if identifier.startswith("ark:/"):
    id = identifier[5:]
    predicate = validateArk
    prefix = "ark:/"
  elif identifier.startswith("doi:"):
    id = identifier[4:]
    predicate = validateDoi
    prefix = "doi:"
  elif identifier.startswith("uuid:"):
    id = identifier[5:]
    predicate = validateUuid
    prefix = "uuid:"
  else:
    assert False, "unhandled case"
  l = []
  for i in range(1, len(id)+1):
     if predicate(id[:i]) == id[:i]: l.append(prefix + id[:i])
  return l

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

def desentencify (s):
  """
  Turns a string that looks like a sentence (initial capital letter,
  period at the end) into a phrase.  Fallible, but tries to be
  careful.
  """
  if len(s) >= 2 and s[0].isupper() and not s[1].isupper():
    s = s[0].lower() + s[1:]
  if s.endswith("."):
    return s[:-1]
  else:
    return s

# The following dictionary maps Identifier model fields to ANVL
# labels, to the extent possible.

_modelAnvlLabelMapping = {
  "owner": "_owner",
  "ownergroup": "_ownergroup",
  "createTime": "_created",
  "updateTime": "_updated",
  "status": "_status",
  "unavailableReason": "_status",
  "exported": "_export",
  "datacenter": "_datacenter",
  "crossrefStatus": "_crossref",
  "crossrefMessage": "_crossref",
  "target": "_target",
  "profile": "_profile",
  "agentRole": "_ezid_role"
}

def formatValidationError (exception, convertToAnvlLabels=True):
  """
  Formats a Django validation error into a single-line string.  If
  'convertToAnvlLabels' is true, an attempt is made to convert any
  model field names referenced in the error to their ANVL
  counterparts.
  """
  l = []
  for entry in exception:
    if type(entry) is tuple:
      l.append("%s: %s" % (_modelAnvlLabelMapping.get(entry[0], entry[0])\
        if convertToAnvlLabels else entry[0],
        ", ".join(desentencify(s) for s in entry[1])))
    else:
      l.append(desentencify(entry))
  return oneLine("; ".join(l))

_illegalAsciiCharsRE = re.compile("[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\xFF]")

def validateAsciiSafeCharset (s):
  """
  Returns true if the given ASCII string contains only non-control
  7-bit characters.
  """
  return _illegalAsciiCharsRE.search(s) == None

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

def xmlEscape (s):
  """
  Suitably escapes a string for inclusion in an XML element or
  attribute (assuming attributes are delimited by double quotes).
  """
  return xml.sax.saxutils.escape(s, { "\"": "&quot;" })

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

def formatTimestampZulu (t):
  """
  Returns a Unix timestamp in ISO 8601 UTC format.
  """
  return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))

def parseTimestampZulu (s, allowDateOnly=False):
  """
  Parses a time (or just a date, if 'allowDateOnly' is true) in ISO
  8601 UTC format and returns a Unix timestamp.  Raises an exception
  on parse error.
  """
  t = None
  if allowDateOnly:
    try:
      t = time.strptime(s, "%Y-%m-%d")
    except:
      pass
  if t == None: t = time.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
  return calendar.timegm(t)
