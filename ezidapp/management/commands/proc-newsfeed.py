#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Interface to the EZID RSS news feed.

The RSS feed configured in settings NEWSFEED_URL is periodically downloaded and checked
for new entries. Any new entries are added to the EZID database.
"""
import datetime
import logging
import time

import django.conf
import feedparser

import ezidapp.management.commands.proc_base
import ezidapp.models.identifier
import ezidapp.models.news_feed
import impl.log

log = logging.getLogger(__name__)


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    name = __name__
    setting = 'DAEMONS_NEWSFEED_ENABLED'

    def run(self):
        while not self.terminated():
            try:
                feed = feedparser.parse(django.conf.settings.NEWSFEED_URL)
                for entry in feed.entries:
                    if not ezidapp.models.news_feed.NewsFeed.objects.filter(
                        feed_id=entry.id
                    ).exists():
                        ezidapp.models.news_feed.NewsFeed(
                            feed_id=entry.id,
                            published=datetime.datetime.fromtimestamp(
                                time.mktime(entry.published_parsed)
                            ),
                            title=entry.title,
                            link=entry.link,
                        ).save()
            except Exception as e:
                log.error('Exception')
                impl.log.otherError("newsfeed._newsDaemon", e)

            self.sleep(django.conf.settings.NEWSFEED_POLLING_INTERVAL)
