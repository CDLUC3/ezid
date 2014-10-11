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
_noItem = ("No news available", None)
_url = None
_pollingInterval = None
_threadName = None
_item = None

def _newsDaemon ():
  global _item
  while _enabled and threading.currentThread().getName() == _threadName:
    try:
      feed = feedparser.parse(_url)
      if len(feed.entries) > 0:
        item = (feed.entries[0].title, feed.entries[0].link)
      else:
        item = _noItem
    except Exception, e:
      log.otherError("newsfeed._newsDaemon", e)
      item = _noItem
    _lock.acquire()
    try:
      if threading.currentThread().getName() == _threadName: _item = item
    finally:
      _lock.release()
    time.sleep(_pollingInterval)

def _loadConfig ():
  global _enabled, _url, _pollingInterval, _threadName, _item
  _enabled = django.conf.settings.DAEMON_THREADS_ENABLED and\
    config.config("daemons.newsfeed_enabled").lower() == "true"
  if _enabled:
    _url = config.config("newsfeed.url")
    _pollingInterval = int(config.config("newsfeed.polling_interval"))
    _lock.acquire()
    try:
      _item = _noItem
      _threadName = uuid.uuid1().hex
      t = threading.Thread(target=_newsDaemon, name=_threadName)
      t.setDaemon(True)
      t.start()
    finally:
      _lock.release()
  else:
    _item = _noItem

_loadConfig()
config.addLoader(_loadConfig)

def getLatestItem ():
  """
  Returns the latest news item as a tuple (title, URL).  The URL may
  be None.
  """
  return _item
