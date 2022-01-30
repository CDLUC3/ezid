#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Interface to the "egg" (binder) portion of noid

A note on encodings. Identifiers and metadata elements (both names and values) are sent
to noid in encoded form; see util.encode{3,4}. Metadata elements received from void are
UTF-8-encoded and utilize percent-encoding. Though this received encoding does not
exactly match the transmitted encoding, the decoding performed by util.decode is
nevertheless compatible and so we use it. (Consider a Python Unicode value
u"Greg%Jan\xe9e". This is sent as "Greg%25Jan%C3%A9e" but received back as
"Greg%25Jan\xc3\xa9e", which, when percent- and UTF-8-decoded, yields the original
value.)

This module performs whitespace processing. Leading and trailing whitespace is stripped
from both element names and values. Empty names are not allowed. Setting an empty
value causes the element to be deleted; as a consequence, empty values are never
returned.
"""

import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.response

import django.conf

import impl.log
import impl.util

log = logging.getLogger(__name__)

DECODE_RX = re.compile("\^([0-9a-fA-F][0-9a-fA-F])?")


@impl.log.stacklog
def _issue(method, operations):
    log.info('_issue', repr(method), repr(operations))
    # noinspection PyUnresolvedReferences
    r = urllib.request.Request(django.conf.settings.BINDER_URL + "?-")
    r.get_method = lambda: method
    # noinspection PyTypeChecker
    r.add_header(
        "Authorization",
        impl.util.basic_auth(
            django.conf.settings.BINDER_USERNAME,
            django.conf.settings.BINDER_PASSWORD,
        ),
    )

    r.add_header("Content-Type", "text/plain")

    s = ""

    l = []
    for o in operations:
        # o = (identifier, operation [,element [, value]])
        s = f":hx% {impl.util.encode4(o[0])}.{o[1]}"
        if len(o) > 2:
            s += " " + impl.util.encode4(o[2])
        if len(o) > 3:
            s += " " + impl.util.encode3(o[3])
        l.append(s)
    r.data = "\n".join(l).encode('utf-8')

    for i in range(django.conf.settings.BINDER_NUM_ATTEMPTS):
        c = None
        try:
            c = urllib.request.urlopen(r)
            s = c.readlines()
        except Exception:
            # noinspection PyTypeChecker
            if i == django.conf.settings.BINDER_NUM_ATTEMPTS - 1:
                raise
        else:
            break
        finally:
            if c:
                c.close()
        # noinspection PyTypeChecker
        time.sleep(django.conf.settings.BINDER_REATTEMPT_DELAY)

    return s


def _error(operation, s):
    return f'unexpected return from noid egg "{operation}":\n ' f'{"".join(str(x) for x in s)}'


def identifierExists(id_str):
    """Return true if an identifier (given in normalized, qualified form,
    e.g., "doi:10.1234/FOO") exists.

    Raises an exception on error.
    """
    # The question of whether an identifier exists or not is surprisingly elusive. Noid will return
    # information for any identifier string, so we can't use that as a test. Instead, we test for
    # the presence of metadata. EZID populates a newly-created identifier with multiple metadata
    # fields. (Noid adds its own internal metadata fields, but only in response to EZID adding
    # fields.)
    #
    # The 'getElements' and 'deleteIdentifier' functions below work to maintain the invariant
    # property that either an identifier has EZID metadata (along with noid-internal metadata) or it
    # has no metadata at all.
    s = _issue("GET", [(id_str, "fetch")])
    assert (
        len(s) >= 4
        and s[0].startswith("# id:")
        and s[-3].startswith("# elements bound under")
        and s[-2] == "egg-status: 0\n"
    ), _error("fetch", s)
    m = re.search(": (\\d+)\n$", s[-3])
    assert m, _error("fetch", s)
    return m.group(1) != "0"


def setElements(id_str, d):
    """Bind metadata elements to an id_str (given in normalized, qualified
    form, e.g., "doi:10.1234/FOO").

    The elements should be given in a dictionary that maps names to
    values. Raises an exception on error.
    """
    batchSetElements([(id_str, d)])


def batchSetElements(batch):
    """Similar to 'setElements' above, but operates on multiple identifiers in
    one request.

    'batch' should be a list of (identifier, name/value dictionary)
    tuples.
    """
    bind_list = []
    for identifier, d in batch:
        for e, v in list(d.items()):
            e = e.strip()
            assert len(e) > 0, "empty label"
            v = v.strip()
            if v == "":
                bind_list.append((identifier, "rm", e))
            else:
                bind_list.append((identifier, "set", e, v))
    s = _issue("POST", bind_list)
    assert len(s) >= 2 and s[-2] == b"egg-status: 0\n", _error("set/rm", s)


def getElements(identifier):
    """Return all metadata elements (in the form of a dictionary) that are
    bound to an identifier (given in normalized, qualified form, e.g.,
    "doi:10.1234/FOO"), or None if the identifier doesn't exist.

    Raises an exception on error.
    """
    # See the comment under 'identifierExists' above.
    s = _issue("GET", [(identifier, "fetch")])
    assert (
        len(s) >= 4
        and s[0].startswith("# id:")
        and s[-3].startswith("# elements bound under")
        and s[-2] == "egg-status: 0\n"
    ), _error("fetch", s)
    m = re.search(": (\\d+)\n$", s[-3])
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
            d[impl.util.decode(e)] = impl.util.decode(v.strip())
        # There had better be at least one non-noid-internal binding.
        assert len(d) > 0, _error("fetch", s)
        return d


def deleteIdentifier(identifier):
    """Delete all metadata elements (including noid-internal elements) bound
    to an identifier (given in normalized, qualified form, e.g.,
    "doi:10.1234/FOO").

    After calling this function, the identifier is deleted in the sense
    that identifierExists(identifier) will return False and
    getElements(identifier) will return None. As far as noid is
    concerned, however, the identifier still exists and metadata
    elements can be re-bound to it in the future. Raises an exception
    on error.
    """
    s = _issue("POST", [(identifier, "purge")])
    assert len(s) >= 2 and s[-2] == "egg-status: 0\n", _error("purge", s)
    # See the comment under 'identifierExists' above.
    assert not identifierExists(
        identifier
    ), f"noid egg 'purge' operation on {identifier} left remaining bindings"


def batchDeleteIdentifier(batch):
    """Similar to 'deleteIdentifier' above, but deletes a list of identifiers
    in one request."""
    # The following code does not verify that all bindings have been
    # removed as 'deleteIdentifier' does above. But that code is just a
    # guard against noid API changes, and having it in one place is
    # sufficient.
    s = _issue("POST", [(identifier, "purge") for identifier in batch])
    assert len(s) >= 2 and s[-2] == "egg-status: 0\n", _error("purge", s)


def ping():
    """Test the server, returning "up" or "down"."""
    try:
        s = _issue("GET", [])
        assert len(s) >= 2 and s[-2] == "egg-status: 0\n"
        return "up"
    except Exception:
        return "down"


def _decodeRewriter(m):
    assert len(m.group(0)) == 3, "circumflex decode error"
    return chr(int(m.group(0)[1:], 16))


def decodeRaw(s):
    """Decode an identifier or metadata element name as stored internally in
    noid.

    Raises AssertionError and UnicodeDecodeError.
    """
    return DECODE_RX.sub(_decodeRewriter, s)
