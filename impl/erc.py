# =============================================================================
#
# EZID :: erc.py
#
# Support for Electronic Resource Citation (ERC) or "kernel" metadata.
# See <http://dublincore.org/groups/kernel/spec/>.
#
# The focus of this module is on basic structural parsing of ERC
# records, not parsing or processing of metadata values.  Thus, of the
# features listed in the ERC specification, only the following are
# supported:
#
#   basic ANVL/ERC syntax
#   repeated values (they're concatenated or listed)
#   percent encoding
#   expansion blocks
#   case insensitivity of labels (they're lowercased)
#   spaces in labels
#
# Not supported:
#
#   multiple records in an input string (only the first record is processed)
#   abbreviated (one-line) syntax
#   character repertoire restrictions
#   standardized value codes
#   standardized values substituted in place of missing values
#   label synonym codes
#   marker characters
#   initial marker character conventions
#   word reordering
#
# Extensions:
#
#   The "erc:" header may be omitted.
#
# Ideally this module would use anvl.py for basic parsing, but there
# are too many differences between ANVL as EZID uses it and ANVL/ERC
# (e.g., in the percent encodings supported) for that to be possible.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2012, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import re


class ErcParseException(Exception):
    pass


_encodings = {
    "sp": " ",
    "ex": "!",
    "dq": "\"",
    "ns": "#",
    "do": "$",
    "pe": "%",
    "am": "&",
    "sq": "'",
    "op": "(",
    "cp": ")",
    "as": "*",
    "pl": "+",
    "co": ",",
    "pd": ".",
    "sl": "/",
    "cn": ":",
    "sc": ";",
    "lt": "<",
    "eq": "=",
    "gt": ">",
    "qu": "?",
    "at": "@",
    "ox": "[",
    "ls": "\\",
    "cx": "]",
    "vb": "|",
    "nu": chr(0),
    "%": "%",
    "_": "",
}

_encodingRE = re.compile("%([a-z][a-z]|%|_)")


def _decodeNonExpansionBlock(s):
    return _encodingRE.sub(lambda c: _encodings.get(c.group(1), c.group(0)), s)


_whitespaceRE = re.compile("\\s")


def _decodeExpansionBlock(s):
    return _whitespaceRE.sub("", s)


def _decode(s):
    r = ""
    j = 0
    while j < len(s):
        i = s.find("%{", j)
        if i < 0:
            i = len(s)
        r += _decodeNonExpansionBlock(s[j:i])
        j = s.find("%}", i + 2)
        if j < 0:
            j = len(s)
        r += _decodeExpansionBlock(s[i + 2 : j])
        j += 2
    return r


_spaceRE = re.compile("\\s+")


def _decodeLabel(s):
    return _spaceRE.sub("_", _decode(s).strip()).lower()


def parse(s, concatenateValues=True):
    """Parses an ANVL/ERC record (represented as a single string) and returns a
    dictionary of metadata element name/value pairs.

    If 'concatenateValues' is true, repeated values for a given element
    are concatenated into a single string; otherwise, they're left as a
    list.  If the input contains multiple records, only the first is
    processed.  Raises ErcParseException (defined in this module).
    """
    d = {}
    k = None
    for l in s.splitlines():
        if len(l) == 0:
            break
        elif l[0] == "#":
            pass
        elif l[0].isspace():
            if k is None:
                raise ErcParseException("no previous label for continuation line")
            v = l.strip()
            if v != "":
                if d[k][-1] == "":
                    d[k][-1] = v
                else:
                    d[k][-1] += " " + v
        else:
            if ":" not in l:
                raise ErcParseException("no colon in line")
            k, v = l.split(":", 1)
            k = _decodeLabel(k)
            if k == "":
                raise ErcParseException("empty label")
            if k not in d:
                d[k] = []
            d[k].append(v.strip())
    if concatenateValues:
        for k in d:
            d[k] = " ; ".join(v for v in [_decode(v) for v in d[k]] if v != "")
        if "erc" in d and d["erc"] == "":
            del d["erc"]
    else:
        for k in d:
            d[k] = [v for v in [_decode(v) for v in d[k]] if v != ""]
        if "erc" in d and len(d["erc"]) == 0:
            del d["erc"]
    return d
