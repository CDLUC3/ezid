# =============================================================================
#
# EZID :: handle_system.py
#
# Handle System utilities.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2017, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------
import io
import urllib.error
import urllib.parse
import urllib.request
import urllib.response


class _RedirectCatcher(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            req.get_full_url(),
            code,
            "redirect",
            headers,
            io.BytesIO(fp.read().encode('utf-8')),
        )


def getRedirect(doi):
    """Returns the target URL for an identifier as recorded with the global DOI
    resolver (doi.org), or None if the identifier isn't found.

    'doi' should be a scheme-less DOI identifier, e.g., "10.1234/FOO".
    Raises an exception on other errors.
    """
    o = urllib.request.build_opener(_RedirectCatcher())
    r = urllib.request.Request("https://doi.org/" + urllib.parse.quote(doi, ":/"))
    c = None
    try:
        c = o.open(r)
        c.read()
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307):
            assert "location" in e.headers, "redirect has no Location header"
            return e.headers["location"]
        elif e.code == 404:
            return None
        else:
            raise
    else:
        assert False, "expecting a redirect from doi.org"
    finally:
        if c:
            c.close()
