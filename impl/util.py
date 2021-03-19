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
import base64
import calendar
import datetime
import logging
import re
import sys
import time
import xml.sax.saxutils
import zlib

import lxml.etree

maxIdentifierLength = 255

_doiPattern = re.compile('10\.[1-9]\d{3,4}/[!"$->@-~]+$')

logger = logging.getLogger(__name__)


def validateDoi(doi):
    """If the supplied string (e.g., "10.5060/foo") is a syntactically valid
    scheme-less DOI identifier, returns the canonical form of the identifier
    (namely, uppercased).

    Otherwise, returns None.
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

    assert isinstance(doi, str)

    if not _doiPattern.match(doi) or doi[-1] == "\n":
        return None
    if "//" in doi or doi.endswith("/"):
        return None
    # We should probably test the length of the shadow ARK as well (it
    # may be longer than the DOI due to extra percent encoding), but
    # don't at present.
    if len(doi) > maxIdentifierLength - 4:
        return None
    return doi.upper()


_arkPattern1 = re.compile("((?:\d{5}(?:\d{4})?|[bcdfghjkmnpqrstvwxz]\d{4})/)([!-~]+)$")
_arkPattern2 = re.compile("\./|/\.")
_arkPattern3 = re.compile("([./])[./]+")
_arkPattern4 = re.compile("^[./]|[./]$")
_arkPattern5 = re.compile("%[0-9a-fA-F][0-9a-fA-F]|.")
_arkPattern6 = re.compile("[0-9a-zA-Z=*+@_$~]")
_arkPattern7 = re.compile("[0-9a-zA-Z=*+@_$~./]")


def _normalizeArkPercentEncoding(m):
    assert isinstance(m, re.Match)

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
            return f"%{ord(s):02x}"


def validateArk(ark):
    """If the supplied string (e.g., "13030/foo") is a syntactically valid
    scheme-less ARK identifier, returns the canonical form of the identifier.

    Otherwise, returns None.
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

    assert isinstance(ark, str)

    logger.debug('validateArk(): {}'.format(ark))

    m = _arkPattern1.match(ark)
    if not m or ark[-1] == "\n":
        return None
    p = m.group(1)
    s = m.group(2)
    # Hyphens are insignificant.
    s = s.replace("-", "")
    # Dissimilar adjacent structural characters are not allowed.
    if _arkPattern2.search(s):
        return None
    # Consolidate adjacent structural characters.
    s = _arkPattern3.sub("\\1", s)
    # Eliminate leading and trailing structural characters.
    s = _arkPattern4.sub("", s)
    if len(s) == 0:
        return None
    # Normalize percent-encodings.
    try:
        s = _arkPattern5.sub(_normalizeArkPercentEncoding, s)
    except AssertionError:
        return None
    if len(p) + len(s) > maxIdentifierLength - 5:
        return None
    return p + s


_uuidPattern = re.compile("[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$", re.I)


def validateUuid(id_str):
    """If the supplied string (e.g., "f81d4fae-7dec-11d0-a765-00a0c91e6bf6") is
    a syntactically valid scheme-less UUID identifier as defined by RFC 4122.

    <http://www.ietf.org/rfc/rfc4122.txt>, returns the canonical form of
    the identifier (namely, lowercased).  Otherwise, returns None.
    """
    logger.debug('validateUuid(): {}'.format(id_str))

    if _uuidPattern.match(id_str) and id_str[-1] != "\n":
        return id_str.lower()
    else:
        return None


def validateIdentifier(identifier):
    """If the supplied string is any type of qualified, syntactically valid
    identifier, returns the canonical form of the identifier.

    Otherwise, returns None.
    """
    logger.debug('validateIdentifier(): {}'.format(identifier))

    if identifier.startswith("ark:/"):
        s = validateArk(identifier[5:])
        if s is not None:
            return "ark:/" + s
        else:
            return None
    elif identifier.startswith("doi:"):
        s = validateDoi(identifier[4:])
        if s is not None:
            return "doi:" + s
        else:
            return None
    elif identifier.startswith("uuid:"):
        s = validateUuid(identifier[5:])
        if s is not None:
            return "uuid:" + s
        else:
            return None
    else:
        return None


def validateShoulder(shoulder):
    """Returns True if the supplied string is a valid shoulder, which is to
    say, if the string is a certain allowable prefix of a qualified,
    syntactically valid identifier."""
    # Strategy: a shoulder is valid if adding a single character yields
    # a valid identifier.
    logger.debug('validateShoulder(): {}'.format(shoulder))

    if shoulder.startswith("ark:/"):
        id_str = shoulder[5:] + "x"
        return validateArk(id_str) == id_str
    elif shoulder.startswith("doi:"):
        id_str = shoulder[4:] + "X"
        return validateDoi(id_str) == id_str
    elif shoulder == "uuid:":
        return True
    else:
        return False


def inferredShoulder(identifier):
    """Given a normalized, qualified identifier (e.g., "ark:/12345/xy7qz"),
    infers and returns the identifier's shoulder (e.g., "ark:/12345/xy").

    This is typically the identifier up to the first two characters
    following the NAAN- or prefix-separating slash.
    """
    if identifier.startswith("ark:/"):
        return re.match(
            "ark:/(\d{5}(\d{4})?|[b-k]\d{4})/[0-9a-zA-Z]{0,2}", identifier
        ).group(0)
    elif identifier.startswith("doi:"):
        return re.match("doi:10\.[1-9]\d{3,4}/[0-9A-Z]{0,2}", identifier).group(0)
    else:
        return identifier.split(":")[0] + ":"


datacenterSymbolRE = re.compile(
    "^([A-Z][-A-Z0-9]{0,6}[A-Z0-9])\.([A-Z][-A-Z0-9]{0,6}[A-Z0-9])$", re.I
)
maxDatacenterSymbolLength = 17


def validateDatacenter(symbol):
    """If the supplied string (e.g., "CDL.BUL") is a valid DataCite datacenter
    symbol, returns the canonical form of the symbol (namely, uppercased).

    Otherwise, returns None.
    """
    if datacenterSymbolRE.match(symbol) and symbol[-1] != "\n":
        return symbol.upper()
    else:
        return None


def _percentEncodeCdr(m):
    s = m.group(0)
    return s[0] + "".join(f"%{ord(c):02x}" for c in s[1:])


def doi2shadow(doi):
    """Given a scheme-less DOI identifier (e.g., "10.5060/FOO"), returns the
    corresponding scheme-less shadow ARK identifier (e.g., "b5060/foo").

    The returned identifier is in canonical form.
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
    logger.debug('doi2shadow(): {}'.format(doi))

    beta_numeric_char = "bcdfghjkmnpqrstvwxz"
    doi_prefix = doi.split("/")[0]
    i = len(doi_prefix) + 1
    if doi[7] == "/":
        p = "b" + doi[3:i]
    else:
        if i == 9:
            p = beta_numeric_char[(ord(doi[3]) - ord("0"))] + doi[4:i]
        elif i == 10:
            p = (
                beta_numeric_char[
                    ((ord(doi[3]) - ord("0")) * 10) + (ord(doi[4]) - ord("0"))
                ]
                + doi[5:i]
            )
    s = doi[i:].replace("%", "%25").replace("-", "%2d").lower()
    s = _arkPattern4.sub(lambda c: f"%{ord(c.group(0)):02x}", s)
    s = _arkPattern3.sub(_percentEncodeCdr, s)
    # noinspection PyUnboundLocalVariable
    a = validateArk(p + s)
    assert a is not None, "shadow ARK failed validation"
    return a


_hexDecodePattern = re.compile("%([0-9a-fA-F][0-9a-fA-F])")


def shadow2doi(ark):
    """Given a scheme-less shadow ARK identifier for a DOI (e.g., "b5060/foo"),
    returns the corresponding scheme-less DOI identifier (e.g., "10.5060/FOO").

    The returned identifier is in canonical form.
    """
    logger.debug('shadow2doi(): {}'.format(ark))

    beta_str = 'bcdfghjkmnpqrstvwxz'
    m = re.match(r'([{}])(.*)/(.*)$'.format(beta_str), ark)
    assert m, f'Invalid scheme-less shadow ARK identifier for a DOI: {ark}'
    beta_char, naan_str, prefix_str = m.groups()
    c = '' if beta_char == 'b' else beta_str.find(beta_char)
    doi = '10.{}{}/{}'.format(c, naan_str, prefix_str)
    return _hexDecodePattern.sub(lambda c: chr(int(c.group(1), 16)), doi).upper()


_shadowedDoiPattern = re.compile("ark:/[bcdfghjkmnpqrstvwxz]")  # see _arkPattern1 above


def normalizeIdentifier(id_str):
    """Similar to 'validateIdentifier': if the supplied string is any type of
    qualified, syntactically valid identifier, returns the canonical form of
    the identifier.

    However, if the identifier is a shadow ARK, this function instead
    returns (the canonical form of) the shadowed identifier.  On any
    kind of error, returns None.
    """
    logger.debug('normalizeIdentifier(): {}'.format(id_str))

    id_str = validateIdentifier(id_str)
    if id_str is None:
        return None
    if id_str.startswith("ark:/"):
        # The reverse shadow function doesn't check that the supplied
        # identifier is indeed a valid shadow ARK, so we check that the
        # returned identifier is valid and produces the same shadow ARK.
        if _shadowedDoiPattern.match(id_str):
            doi = shadow2doi(id_str[5:])
            if validateDoi(doi) is not None and doi2shadow(doi) == id_str[5:]:
                return "doi:" + doi
            else:
                return None
        else:
            return id_str
    else:
        return id_str


def explodePrefixes(id_str):
    """Given a normalized, qualified identifier (e.g., "ark:/12345/x/yz"),
    returns a list of all prefixes of the identifier that are syntactically
    valid identifiers (e.g., ["ark:/12345/x", "ark:/12345/x/y",
    "ark:/12345/x/yz"])."""
    if id_str.startswith("ark:/"):
        id = id_str[5:]
        predicate = validateArk
        prefix = "ark:/"
    elif id_str.startswith("doi:"):
        id = id_str[4:]
        predicate = validateDoi
        prefix = "doi:"
    elif id_str.startswith("uuid:"):
        id = id_str[5:]
        predicate = validateUuid
        prefix = "uuid:"
    else:
        assert False, "unhandled case"
    l = []
    for i in range(1, len(id) + 1):
        if predicate(id[:i]) == id[:i]:
            l.append(prefix + id[:i])
    return l


def _encode(pattern, s):
    # print(f'encode: {repr(s)}')
    # s = s.encode('utf-8') if isinstance(s, str) else s

    # return pattern.sub(lambda c: f'{ord(c.group(0))}:02X', s)
    return pattern.sub(lambda c: f'%{ord(c.group(0)):02X}', s)


_pattern1 = re.compile("%|[^ -~]")


def encode1(s):
    """utf-8 encodes a Unicode string, then percent-encodes all non-graphic
    ASCII characters except space.

    This form of encoding is used for log file exception strings.
    """
    return _encode(_pattern1, s)
    # .decode('utf-8')


_pattern2 = re.compile("%|[^!-~]")


def encode2(s):
    """Like encode1, but percent-encodes spaces as well.

    This form of encoding is used for log file record fields other than
    exception strings.
    """
    return _encode(_pattern2, s)


_pattern3 = re.compile('[%\'"\\\\&@|;()[\\]=]|[^!-~]')


def encode3(s):
    """Like encode2, but percent-encodes ('), ("), (\), (&), (@), (|), (;) ((),
    ()), ([), (]), and (=) as well.

    This form of encoding is used for noid element values.
    """
    assert isinstance(s, str)
    return _encode(_pattern3, s)


_pattern4 = re.compile('[%\'"\\\\&@|;()[\\]=:<]|[^!-~]')


def encode4(s):
    """Like encode3, but percent-encodes (:) and (<) as well.

    This form of encoding is used for noid identifiers and noid element
    names.
    """
    assert isinstance(s, str)
    return _encode(_pattern4, s)


class PercentDecodeError(Exception):
    pass


_hexDigits = "0123456789ABCDEFabcdef"
_hexMapping = dict((a + b, chr(int(a + b, 16))) for a in _hexDigits for b in _hexDigits)


def decode(s):
    """Decodes a string that was encoded by encode{1,2,3,4}.

    Raises PercentDecodeError (defined in this module) and
    UnicodeDecodeError.
    """
    l = s.split("%")
    r = [l[0]]
    for p in l[1:]:
        try:
            r.append(_hexMapping[p[:2]])
            r.append(p[2:])
        except KeyError:
            raise PercentDecodeError()
    return "".join(r)


def toExchange(metadata, identifier=None):
    """Returns an exchange representation of a metadata dictionary, which is a
    string of the format "label value label value ..." in which labels and
    values are percent-encoded via encode{3,4} above, and are separated by
    single spaces.

    Labels and values are stripped before being encoded; empty labels
    are not permitted and labels with empty values are discarded.  If
    'identifier' is not None, it is inserted as the first token in the
    string; it is not encoded.
    """
    l = []
    if identifier is not None:
        # We're assuming here that the identifier contains no spaces or
        # newlines, but we don't check that.
        l.append(identifier)
    for k, v in list(metadata.items()):
        k = k.strip()
        assert len(k) > 0, "empty label"
        v = v.strip()
        if len(v) > 0:
            l.append(encode4(k))
            l.append(encode3(v))
    return " ".join(l)


def fromExchange(line, identifierEmbedded=False):
    """Reconstitutes a metadata dictionary from an exchange representation.

    If 'identifierEmbedded' is True, the first token is assumed to be an
    identifier, and the return is a tuple (identifier, dictionary).
    Otherwise, the return is simply a dictionary.  N.B.: this function
    only partially checks the input.
    """
    if len(line) > 0 and line[-1] == "\n":
        line = line[:-1]
    if len(line) == 0:
        assert not identifierEmbedded, "wrong number of tokens"
        return {}
    v = line.split(" ")
    if identifierEmbedded:
        assert len(v) % 2 == 1, "wrong number of tokens"
        assert len(v[0]) > 0, "empty token"
        identifier = v[0]
        start = 1
    else:
        assert len(v) % 2 == 0, "wrong number of tokens"
        start = 0
    d = {}
    for i in range(start, len(v), 2):
        assert len(v[i]) > 0 and len(v[i + 1]) > 0, "empty token"
        d[decode(v[i])] = decode(v[i + 1])
    if identifierEmbedded:
        # noinspection PyUnboundLocalVariable
        return identifier, d
    else:
        return d


def blobify(metadata):
    """Converts a metadata dictionary to a binary, compressed string, or
    "blob."  Labels and values are stripped; labels with empty values are
    discarded."""
    assert isinstance(metadata, dict)
    return zlib.compress(toExchange(metadata).encode('utf-8'))


def deblobify(blob, decompressOnly=False):
    """Converts a blob back to a metadata dictionary.

    If 'decompressOnly' is True, the metadata is returned in exchange
    representation form.
    """
    v = zlib.decompress(blob)
    if decompressOnly:
        return v
    else:
        return fromExchange(v)


def oneLine(s):
    """Replaces newlines in a string with spaces."""
    assert isinstance(s, str)
    return re.sub("\s", " ", s)


def formatException(exception):
    """Formats an exception into a single-line string."""
    s = oneLine(str(exception)).strip()
    if len(s) > 0:
        s = ": " + s
    return type(exception).__name__ + s


def desentencify(s):
    """Turns a string that looks like a sentence (initial capital letter,
    period at the end) into a phrase.

    Fallible, but tries to be careful.
    """
    assert isinstance(s, str)
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
    "agentRole": "_ezid_role",
}


def formatValidationError(exception, convertToAnvlLabels=True):
    """Formats a Django validation error into a single-line string.

    If 'convertToAnvlLabels' is true, an attempt is made to convert any
    model field names referenced in the error to their ANVL
    counterparts.
    """
    l = []
    for entry in exception:
        if type(entry) is tuple:
            l.append(
                "{}: {}".format(
                    _modelAnvlLabelMapping.get(entry[0], entry[0])
                    if convertToAnvlLabels
                    else entry[0],
                    ", ".join(desentencify(s) for s in entry[1]),
                )
            )
        else:
            l.append(desentencify(entry))
    return oneLine("; ".join(l))


_illegalAsciiCharsRE = re.compile("[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\xFF]")


def validateAsciiSafeCharset(s):
    """Returns true if the given ASCII string contains only non-control 7-bit
    characters."""
    assert isinstance(s, str)
    return _illegalAsciiCharsRE.search(s) is None


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

_illegalUnichrs = [
    (0x00, 0x08),
    (0x0B, 0x0C),
    (0x0E, 0x1F),
    (0x7F, 0x84),
    (0x86, 0x9F),
    (0xFDD0, 0xFDDF),
    (0xFFFE, 0xFFFF),
]
if sys.maxunicode >= 0x10000:
    _illegalUnichrs.extend(
        [
            (0xD800, 0xDFFF),
            (0x1FFFE, 0x1FFFF),
            (0x2FFFE, 0x2FFFF),
            (0x3FFFE, 0x3FFFF),
            (0x4FFFE, 0x4FFFF),
            (0x5FFFE, 0x5FFFF),
            (0x6FFFE, 0x6FFFF),
            (0x7FFFE, 0x7FFFF),
            (0x8FFFE, 0x8FFFF),
            (0x9FFFE, 0x9FFFF),
            (0xAFFFE, 0xAFFFF),
            (0xBFFFE, 0xBFFFF),
            (0xCFFFE, 0xCFFFF),
            (0xDFFFE, 0xDFFFF),
            (0xEFFFE, 0xEFFFF),
            (0xFFFFE, 0xFFFFF),
            (0x10FFFE, 0x10FFFF),
        ]
    )

_illegalUnichrsRE = re.compile(
    f"[{''.join('%s-%s' % (chr(low), chr(high)) for low, high in _illegalUnichrs)}]"
)


def validateXmlSafeCharset(s):
    """Returns true if the given Unicode string contains only characters that
    are accepted by XML 1.1."""
    assert isinstance(s, str)
    return _illegalUnichrsRE.search(s) is None


def sanitizeXmlSafeCharset(s):
    """Returns a copy of the given Unicode string in which characters not
    accepted by XML 1.1 have been replaced with spaces."""
    assert isinstance(s, str)
    return _illegalUnichrsRE.sub(" ", s)


if sys.maxunicode >= 0x10000:
    _illegalUnichrsPlusSuppPlanes = _illegalUnichrs + [(0x10000, 0x10FFFF)]
else:
    _illegalUnichrsPlusSuppPlanes = _illegalUnichrs + [(0xD800, 0xDFFF)]

_illegalUnichrsPlusSuppPlanesRE = re.compile(
    "[{}]".format(
        "".join(
            "%s-%s" % (chr(low), chr(high))
            for low, high in _illegalUnichrsPlusSuppPlanes
        )
    )
)


def validateXmlSafeCharsetBmpOnly(s):
    """Returns true if the given Unicode string contains only characters that
    are accepted by XML 1.1 and that are in the Basic Multilingual Plane."""
    assert isinstance(s, str)
    return _illegalUnichrsPlusSuppPlanesRE.search(s) is None


xmlDeclarationRE = re.compile(
    '<\?xml\s+version\s*=\s*([\'"])([-\w.:]+)\\1'
    '(\s+encoding\s*=\s*([\'"])([a-zA-Z][-\w.]*)\\4)?'
    '(\s+standalone\s*=\s*([\'"])(yes|no)\\7)?\s*\?>\s*'
)


def removeXmlEncodingDeclaration(document):
    """Removes the encoding declaration from an XML document if present."""
    assert isinstance(document, str)
    m = xmlDeclarationRE.match(document)
    if m and m.group(3) is not None:
        return document[: m.start(3)] + document[m.end(3) :]
    else:
        return document


def removeXmlDeclaration(document):
    """Removes the entire XML declaration from an XML document if present."""
    assert isinstance(document, str)
    m = xmlDeclarationRE.match(document)
    if m:
        return document[len(m.group(0)) :]
    else:
        return document


def insertXmlEncodingDeclaration(document):
    """Inserts a UTF-8 encoding declaration in an XML document if it lacks one.

    'document' should be an unencoded string and the return is likewise
    an unencoded string.  (Note that, due to the discrepancy between the
    encoding declaration and the encoding of the returned string, to be
    parsed again by lxml, the encoding declaration will need to be
    removed.)
    """
    assert isinstance(document, str)
    m = xmlDeclarationRE.match(document)
    if m:
        if m.group(3) is None:
            return (
                document[: m.end(2) + 1]
                + ' encoding="utf-8"'
                + document[m.end(2) + 1 :]
            )
        else:
            return document
    else:
        return '<?xml version="1.0" encoding="utf-8"?>\n' + document


def parseXmlString(document):
    """Parses an XML document from a string, returning a root element node.

    If a Unicode string is supplied, any encoding declaration in the
    document is discarded and ignored; otherwise, if an encoding
    declaration is present, the parser treats the string as a binary
    stream and decodes it per the declaration.
    """
    assert isinstance(document, str)

    if type(document) is str:
        return lxml.etree.XML(document)
    elif type(document) is str:
        return lxml.etree.XML(removeXmlEncodingDeclaration(document))
    else:
        assert False, "unhandled case"


_extractTransform = None
_extractTransformSource = """<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

<xsl:output method="text" encoding="utf-8"/>
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


def extractXmlContent(document):
    """Extracts all content from an XML document (all attribute values, all
    textual element content) and returns it as a single Unicode string in which
    individual fragments are separated by " ; ".

    Whitespace is normalized throughout per XPath.  The input document
    may be a string or an already-parsed document tree.
    """
    assert isinstance(document, str)

    global _extractTransform
    if _extractTransform is None:
        _extractTransform = lxml.etree.XSLT(lxml.etree.XML(_extractTransformSource))
    if isinstance(document, str):
        document = parseXmlString(document)
    return str(_extractTransform(document)).strip()[:-2]


_datespecRE = re.compile("(\d{4})(?:-(\d\d)(?:-(\d\d))?)?$")


def xmlEscape(s):
    """Suitably escapes a string for inclusion in an XML element or attribute
    (assuming attributes are delimited by double quotes)."""
    assert isinstance(s, str)

    return xml.sax.saxutils.escape(s, {'"': "&quot;"})


def dateToLowerTimestamp(date):
    """Converts a string date of the form YYYY, YYYY-MM, or YYYY-MM-DD to a
    Unix timestamp, or returns None if the date is invalid.

    The returned timestamp is the first (earliest) second within the
    specified time period.  Note that the timestamp may be negative or
    otherwise out of the normal range for Unix timestamps.
    """
    assert isinstance(date, str)

    rm = _datespecRE.match(date)
    if not rm or date[-1] == "\n":
        return None
    y = int(rm.group(1))
    m = int(rm.group(2)) if rm.group(2) is not None else 1
    d = int(rm.group(3)) if rm.group(3) is not None else 1
    try:
        return calendar.timegm(datetime.date(y, m, d).timetuple())
    except ValueError:
        return None


def dateToUpperTimestamp(date):
    """Converts a string date of the form YYYY, YYYY-MM, or YYYY-MM-DD to a
    Unix timestamp, or returns None if the date is invalid.

    The returned timestamp is the last (latest) second within the
    specified time period.  Note that the timestamp may be negative or
    otherwise out of the normal range for Unix timestamps.
    """
    # Overflow and edge cases.
    assert isinstance(date, str)

    if date in ["9999", "9999-12", "9999-12-31"]:
        return calendar.timegm(datetime.datetime(9999, 12, 31, 23, 59, 59).timetuple())
    elif date == "0000":
        return None
    rm = _datespecRE.match(date)
    if not rm or date[-1] == "\n":
        return None
    try:
        y = int(rm.group(1))
        if rm.group(2) is None:
            date = datetime.date(y + 1, 1, 1)
        else:
            m = int(rm.group(2))
            if rm.group(3) is None:
                date = (datetime.date(y, m, 1) + datetime.timedelta(days=31)).replace(
                    day=1
                )
            else:
                date = datetime.date(y, m, int(rm.group(3))) + datetime.timedelta(
                    days=1
                )
        return calendar.timegm(date.timetuple()) - 1
    except ValueError:
        return None


def formatTimestampZulu(t):
    """Returns a Unix timestamp in ISO 8601 UTC format."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def parseTimestampZulu(s, allowDateOnly=False):
    """Parses a time (or just a date, if 'allowDateOnly' is true) in ISO 8601
    UTC format and returns a Unix timestamp.

    Raises an exception on parse error.
    """
    assert isinstance(s, str)

    t = None
    if allowDateOnly:
        try:
            t = time.strptime(s, "%Y-%m-%d")
        except Exception:
            pass
    if t is None:
        t = time.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
    return calendar.timegm(t)


def basic_auth(username, password):
    """Create a HTTP Basic Authentication tuple"""
    return 'Basic ' + base64.b64encode(
        b"".join(
            x.encode("utf-8") if isinstance(x, str) else x
            for x in (username, b":", password)
        )
    ).decode('utf-8')


def parse_basic_auth(auth):
    try:
        b = auth.encode('ascii') if isinstance(auth, str) else auth
        basic_b, base64_b = b.split()
        if basic_b.strip() != b'Basic':
            raise Exception()
        clear_b = base64.decodebytes(base64_b)
        user_b, pw_b = b":".split(clear_b)
        return user_b.decode('utf-8'), pw_b.decode('utf-8')
    except Exception as e:
        raise ValueError(
            f'Invalid basic auth: {auth.decode("utf-8")}. Error: {repr(e)}'
        )
