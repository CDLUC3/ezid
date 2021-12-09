#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Object Relational Mapper (ORM) models for the EZID RSS news feed
"""

import django.db.models

class NewsFeed(django.db.models.Model):
    """Hold items from the EZID RSS news feed
    """
    feed_id = django.db.models.CharField(max_length=255, unique=True)
    published = django.db.models.DateTimeField()
    title = django.db.models.TextField()
    link = django.db.models.URLField()
