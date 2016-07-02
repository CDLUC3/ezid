# =============================================================================
#
# EZID :: newsfeed.py
#
# Interface to the EZID RSS news feed.
#
# This module should be imported at server startup so that its daemon
# thread is started in advance of any UI page requests.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2012, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.conf
import threading
import time
import uuid

import config
import feedparser
import log

_enabled = None
_lock = threading.Lock()
_noItems = [("No news available", None)]
_url = None
_pollingInterval = None
_threadName = None
_items = None

def _newsDaemon ():
  global _items
  while _enabled and threading.currentThread().getName() == _threadName:
    try:
      feed = feedparser.parse(_url)
      if len(feed.entries) > 0:
        items = []
        for i in range(min(len(feed.entries), 3)):
          items.append((feed.entries[i].title, feed.entries[i].link))
      else:
        items = _noItems
    except Exception, e:
      log.otherError("newsfeed._newsDaemon", e)
      items = _noItems
    _lock.acquire()
    try:
      if threading.currentThread().getName() == _threadName: _items = items
    finally:
      _lock.release()
    time.sleep(_pollingInterval)

def _loadConfig ():
  global _enabled, _url, _pollingInterval, _threadName, _items
  _enabled = django.conf.settings.DAEMON_THREADS_ENABLED and\
    config.get("daemons.newsfeed_enabled").lower() == "true"
  if _enabled:
    _url = config.get("newsfeed.url")
    _pollingInterval = int(config.get("newsfeed.polling_interval"))
    _lock.acquire()
    try:
      _items = _noItems
      _threadName = uuid.uuid1().hex
      t = threading.Thread(target=_newsDaemon, name=_threadName)
      t.setDaemon(True)
      t.start()
    finally:
      _lock.release()
  else:
    _items = _noItems

_loadConfig()
config.registerReloadListener(_loadConfig)

def getLatestItems ():
  """
  Returns the latest news items (up to 3 items) as a list of tuples
  [(title, URL), ...].  At least one item is always returned.  The URL
  may be None in a tuple.
  """
  return _items
