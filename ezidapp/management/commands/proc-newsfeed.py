"""Interface to the EZID RSS news feed
"""

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import logging
import threading
import time

import django.conf
import feedparser

import ezidapp.management.commands.proc_base
import impl.log
import impl.nog.util

log = logging.getLogger(__name__)


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    display = 'NewsFeed'
    name = 'newsfeed'
    setting = 'DAEMONS_NEWSFEED_ENABLED'

    def __init__(self):
        super(Command, self).__init__(__name__)

    def add_arguments(self, parser):
        super().add_arguments(parser)

    def handle_daemon(self, *_, **opt):
        pass

    def run(self):
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
                log.exception(' Exception as e')
                self.otherError("newsfeed._newsDaemon", e)
                items = self._noItems

            self._lock.acquire()
            try:
                if threading.currentThread().getName() == self._threadName:
                    _items = items
            finally:
                self._lock.release()

            # noinspection PyTypeChecker
            time.sleep(self._pollingInterval)
