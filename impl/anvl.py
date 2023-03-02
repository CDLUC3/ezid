#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Support for A Name-Value Language (ANVL) text formatting

<http://wiki.ucop.edu/display/Curation/Anvl>.
"""
import datetime
import re


class AnvlParseException(Exception):
    pass


_pattern1 = re.compile("[%:\r\n]")
_pattern2 = re.compile("[%\r\n]")
_pattern3 = re.compile("%([0-9a-fA-F][0-9a-fA-F])?")


def _encode(pattern, s):
    return pattern.sub(lambda c: f"%{ord(c.group(0)):02X}", s)


def _encodeLabel(s):
    return _encode(_pattern1, s)


def _encodeValue(s):
    return _encode(_pattern2, s)


def _decodeRewriter(m):
    if len(m.group(0)) == 3:
        return chr(int(m.group(0)[1:], 16))
    else:
        raise AnvlParseException("percent-decode error")


def _decode(s):
    return _pattern3.sub(_decodeRewriter, s)


def formatPair(label, value):
    """Format a label and value into an ANVL element
    """
    if isinstance(value, datetime.datetime):
        value = value.strftime("%Y.%m.%d_%H:%M:%S")
    return f"{_encodeLabel(label)}: {_encodeValue(value)}\n"


def format(d):
    """Format a dictionary into an ANVL string

    Labels and values are suitably percent-encoded.
    """
    return "".join(formatPair(k, v) for k, v in list(d.items()))


def parse(s):
    """Parse an ANVL string and returns a dictionary

    Labels and values are percent-decoded. Raises AnvlParseException
    (defined in this module).
    """
    d = {}
    k = None
    # We avoid splitlines here to avoid splitting on other weirdo
    # Unicode characters that count as line breaks.
    for l in re.split("\r\n?|\n", s):
        if len(l) == 0:
            k = None
        elif l[0] == "#":
            pass
        elif l[0].isspace():
            if k is None:
                raise AnvlParseException("no previous label for continuation line")
            ll = _decode(l).strip()
            if ll != "":
                if d[k] == "":
                    d[k] = ll
                else:
                    d[k] += " " + ll
        else:
            if ":" not in l:
                raise AnvlParseException("no colon in line")
            k, v = [_decode(w).strip() for w in l.split(":", 1)]
            if len(k) == 0:
                raise AnvlParseException("empty label")
            if k in d:
                raise AnvlParseException("repeated label")
            d[k] = v
    return d


def parseConcatenate(s):
    """Alternate version of 'parse' that concatenates repeated label values and
    separates them by semicolons. For example, the input string:

      a: b
      a: c

    produces the output dictionary:

      { "a": "b ; c" }
    """
    d = {}
    k = None
    # We avoid splitlines here to avoid splitting on other weirdo
    # Unicode characters that count as line breaks.
    for l in re.split("\r\n?|\n", s):
        if len(l) == 0:
            k = None
        elif l[0] == "#":
            pass
        elif l[0].isspace():
            if k is None:
                raise AnvlParseException("no previous label for continuation line")
            ll = _decode(l).strip()
            if ll != "":
                if d[k] == "":
                    d[k] = ll
                else:
                    d[k] += " " + ll
        else:
            if ":" not in l:
                raise AnvlParseException("no colon in line")
            k, v = [_decode(w).strip() for w in l.split(":", 1)]
            if len(k) == 0:
                raise AnvlParseException("empty label")
            if k in d and d[k] != "":
                if v != "":
                    d[k] += " ; " + v
            else:
                d[k] = v
    return d
