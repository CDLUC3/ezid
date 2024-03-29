#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Standalone version of noid_nog.py for use by offline tools
"""

import base64
import urllib.error
import urllib.parse
import urllib.request
import urllib.response


class Minter(object):
    """A minter for a specific shoulder."""

    def __init__(self, url, username, password):
        """Create an interface to the noid nog minter at the supplied URL
        using the supplied credentials."""
        self.url = url
        self.username = username
        self.password = password

    def _addAuthorization(self, request):
        request.add_header(
            "Authorization",
            b"Basic " + (base64.b64encode(self.username + ":" + self.password)),
        )

    def mintIdentifier(self):
        """Mint and returns a scheme-less ARK identifier, e.g.,
        "13030/fk35717n0h".

        Raises an exception on error.
        """
        r = urllib.request.Request(self.url + "?mint%201")
        self._addAuthorization(r)
        c = None
        try:
            c = urllib.request.urlopen(r)
            s = c.readlines()
        finally:
            if c:
                c.close()
        assert (
            len(s) >= 2
            and (s[0].startswith("id:") or s[0].startswith("s:"))
            and s[-2] == "nog-status: 0\n"
        ), "unexpected return from minter, output follows\n" + "".join(s)
        return s[0].split(":", 1)[1].strip()
