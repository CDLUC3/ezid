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

import threading
import time
import uuid

import django.conf
import feedparser

import impl.log


class DaemonBase:
    NAME = None
    IDLE_SLEEP = None

    _noItems = [("No news available", None)]
    _items = _noItems

    class _AbortException(Exception):
        pass

    def __init__(self):
        self._lock = threading.Lock()
        self._stop_requested = threading.Event()
        self._thread = None

    def start(self):
        self._lock.acquire()
        try:
            self._thread = threading.Thread(target=self.async_proc, name=self.NAME)
            self._thread.start()
            self._thread.setDaemon(True)
        finally:
            self._lock.release()

        # if (
        #     django.conf.settings.DAEMON_THREADS_ENABLED
        #     and django.conf.settings.DAEMONS_NEWSFEED_ENABLED
        # ):
        # _url = django.conf.settings.NEWSFEED_URL
        # _pollingInterval = int(django.conf.settings.NEWSFEED_POLLING_INTERVAL)

        # self._lock.acquire()

    def stop(self):
        self._stop_requested.set()

    def stop_is_requested(self):
        return self._stop_requested.isSet()

    def async_proc(self):
        pass

    def _newsDaemon(self):
        while (
            django.conf.settings.CROSSREF_ENABLED
            and threading.currentThread().getName() == self._threadName
        ):
            try:
                feed = feedparser.parse(self._url)
                if len(feed.entries) > 0:
                    items = []
                    for i in range(min(len(feed.entries), 3)):
                        items.append((feed.entries[i].title, feed.entries[i].link))
                else:
                    items = self._noItems
            except Exception as e:
                impl.log.otherError("newsfeed._newsDaemon", e)
                items = self._noItems

            try:
                if threading.currentThread().getName() == self._threadName:
                    _items = items
            finally:
                self._lock.release()
            # noinspection PyTypeChecker
            time.sleep(self._pollingInterval)

    def getLatestItems(self):
        """Returns the latest news items (up to 3 items) as a list of tuples.

        [(title, URL), ...].  At least one item is always returned.  The URL
        may be None in a tuple.
        """
        return self._items
