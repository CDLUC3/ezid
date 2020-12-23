# =============================================================================
#
# EZID :: noid_nog.py
#
# Interface to the "nog" (nice opaque generator) portion of noid.
# Because EZID interacts with multiple nog minters, the interface is
# expressed as a class.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2014, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import base64
import threading
import time
import urllib.request, urllib.error, urllib.parse

from . import config

import logging
from .log import stacklog

_LT = logging.getLogger("tracer")


_lock = threading.Lock()
_minterServers = None
_numAttempts = None
_reattemptDelay = None
_minters = None
_cacheSize = None


def loadConfig():
    global _minterServers, _numAttempts, _reattemptDelay, _minters, _cacheSize
    d = {}
    for ms in config.get("shoulders.minter_servers").split(","):
        p = "minter_server_" + ms
        d[config.get(p + ".url")] = "Basic " + base64.b64encode(
            config.get(p + ".username") + ":" + config.get(p + ".password")
        )
    _minterServers = d
    _numAttempts = int(config.get("shoulders.minter_num_attempts"))
    _reattemptDelay = int(config.get("shoulders.minter_reattempt_delay"))
    _lock.acquire()
    try:
        _minters = {}
    finally:
        _lock.release()
    _cacheSize = int(config.get("shoulders.minter_cache_size"))


def _addAuthorization(request):
    d = _minterServers
    for ms in d:
        if request.get_full_url().startswith(ms):
            request.add_header("Authorization", d[ms])
            break


class Minter(object):
    """A minter for a specific shoulder."""

    def __init__(self, url):
        """Creates an interface to the noid nog minter at the supplied URL."""
        self.url = url
        self.cache = []
        self.lock = threading.Lock()

    @stacklog
    def mintIdentifier(self):
        """Mints and returns a scheme-less ARK identifier, e.g.,
        "13030/fk35717n0h".

        Raises an exception on error.
        """
        self.lock.acquire()
        try:
            cs = _cacheSize
            if len(self.cache) == 0:
                r = urllib.request.Request("%s?mint%%20%d" % (self.url, cs))
                _addAuthorization(r)
                for i in range(_numAttempts):
                    c = None
                    try:
                        c = urllib.request.urlopen(r)
                        s = c.readlines()
                    except:
                        if i == _numAttempts - 1:
                            raise
                    else:
                        break
                    finally:
                        if c:
                            c.close()
                    time.sleep(_reattemptDelay)
                assert (
                    len(s) >= cs + 1
                    and all(l.startswith("id:") or l.startswith("s:") for l in s[:cs])
                    and s[-2] == "nog-status: 0\n"
                ), "unexpected return from minter, output follows\n" + "".join(s)
                self.cache = [l.split(":")[1].strip() for l in s[:cs]]
            id = self.cache[0]
            self.cache = self.cache[1:]
            return id
        finally:
            self.lock.release()

    def ping(self):
        """Tests the minter, returning "up" or "down"."""
        try:
            r = urllib.request.Request(self.url)
            _addAuthorization(r)
            c = None
            try:
                c = urllib.request.urlopen(r)
                s = c.readlines()
            finally:
                if c:
                    c.close()
            assert len(s) >= 2 and s[-2] == "nog-status: 0\n"
            return "up"
        except Exception:
            return "down"


def getMinter(url):
    """Returns a Minter object for a noid nog minter at the supplied URL."""
    _lock.acquire()
    try:
        if url not in _minters:
            _minters[url] = Minter(url)
        return _minters[url]
    finally:
        _lock.release()
