# =============================================================================
#
# EZID :: search_util.py
#
# Search-related utilities.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.db
import time

import config
import log

_reconnectDelay = None

def _loadConfig ():
  global _reconnectDelay
  _reconnectDelay = int(config.get("databases.reconnect_delay"))

_loadConfig()
config.registerReloadListener(_loadConfig)

class AbortException (Exception):
  pass

def withAutoReconnect (functionName, function, continuationCheck=None):
  """
  Calls 'function' and returns the result.  If an operational database
  error is encountered (e.g., a lost connection), the call is repeated
  until it succeeds.  'continuationCheck', if not None, should be
  another function that signals when the attempts should cease by
  raising an exception or returning False.  If 'continuationCheck'
  returns False, this function raises AbortException (defined in this
  module).  'functionName' is the name of 'function' for logging
  purposes.
  """
  while True:
    try:
      return function()
    except django.db.OperationalError, e:
      log.otherError("search_util.withAutoReconnect/" + functionName, e)
      time.sleep(_reconnectDelay)
      if continuationCheck != None and not continuationCheck():
        raise AbortException()
      # In some cases a lost connection causes the thread's database
      # connection object to be permanently screwed up.  The following
      # call solves the problem.  (Note that Django's database
      # connection objects are indexed generically, but are stored
      # thread-local.)
      django.db.connections["search"].close()
