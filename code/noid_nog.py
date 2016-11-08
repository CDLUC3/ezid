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
import time
import urllib2

import config

_minterServers = None
_numAttempts = None
_reattemptDelay = None

def _loadConfig ():
  global _minterServers, _numAttempts, _reattemptDelay
  d = {}
  for ms in config.get("shoulders.minter_servers").split(","):
    p = "minter_server_" + ms
    d[config.get(p + ".url")] = "Basic " +\
      base64.b64encode(config.get(p + ".username") + ":" +\
      config.get(p + ".password"))
  _minterServers = d
  _numAttempts = int(config.get("shoulders.minter_num_attempts"))
  _reattemptDelay = int(config.get("shoulders.minter_reattempt_delay"))

_loadConfig()
config.registerReloadListener(_loadConfig)

def _addAuthorization (request):
  d = _minterServers
  for ms in d:
    if request.get_full_url().startswith(ms):
      request.add_header("Authorization", d[ms])
      break

class Minter (object):
  """
  A minter for a specific shoulder.
  """

  def __init__ (self, url):
    """
    Creates an interface to the noid nog minter at the supplied URL.
    """
    self.url = url

  def mintIdentifier (self):
    """
    Mints and returns a scheme-less ARK identifier, e.g.,
    "13030/fk35717n0h".  Raises an exception on error.
    """
    r = urllib2.Request(self.url + "?mint%201")
    _addAuthorization(r)
    for i in range(_numAttempts):
      c = None
      try:
        c = urllib2.urlopen(r)
        s = c.readlines()
      except:
        if i == _numAttempts-1: raise
      else:
        break
      finally:
        if c: c.close()
      time.sleep(_reattemptDelay)
    assert len(s) >= 2 and (s[0].startswith("id:") or\
      s[0].startswith("s:")) and s[-2] == "nog-status: 0\n",\
      "unexpected return from minter, output follows\n" + "".join(s)
    return s[0].split(":", 1)[1].strip()

  def ping (self):
    """
    Tests the minter, returning "up" or "down".
    """
    try:
      r = urllib2.Request(self.url)
      _addAuthorization(r)
      c = None
      try:
        c = urllib2.urlopen(r)
        s = c.readlines()
      finally:
        if c: c.close()
      assert len(s) >= 2 and s[-2] == "nog-status: 0\n"
      return "up"
    except Exception:
      return "down"
