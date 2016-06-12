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
_noItem = [ ("No news available", None) ]
_url = None
_pollingInterval = None
_threadName = None
_news_items = None

def _newsDaemon ():
  global _news_items
  while _enabled and threading.currentThread().getName() == _threadName:
    try:
      feed = feedparser.parse(_url)
      if len(feed.entries) > 0:
        news_items = [ (feed.entries[0].title, feed.entries[0].link),
                       (feed.entries[1].title, feed.entries[1].link),
                       (feed.entries[2].title, feed.entries[2].link) ]
      else:
        news_items = _noItem
    except Exception, e:
      log.otherError("newsfeed._newsDaemon", e)
      news_items = _noItem
    _lock.acquire()
    try:
      if threading.currentThread().getName() == _threadName: _news_items = news_items
    finally:
      _lock.release()
    time.sleep(_pollingInterval)

def _loadConfig ():
  global _enabled, _url, _pollingInterval, _threadName, _news_items
  _enabled = django.conf.settings.DAEMON_THREADS_ENABLED and\
    config.get("daemons.newsfeed_enabled").lower() == "true"
  if _enabled:
    _url = config.get("newsfeed.url")
    _pollingInterval = int(config.get("newsfeed.polling_interval"))
    _lock.acquire()
    try:
      _news_items = _noItem
      _threadName = uuid.uuid1().hex
      t = threading.Thread(target=_newsDaemon, name=_threadName)
      t.setDaemon(True)
      t.start()
    finally:
      _lock.release()
  else:
    _news_items = _noItem

_loadConfig()
config.registerReloadListener(_loadConfig)

def getLatestItem ():
  """
  Returns the latest news item as a tuple (title, URL).  The URL may
  be None.
  """
  return _news_items
