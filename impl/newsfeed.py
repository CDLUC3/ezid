#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import ezidapp.models.news_feed

NO_NEWS = [("No news available", None)]


def getLatestItems():
    """Returns the latest news items (1 to 3 items)
    [(title, URL), ...].
    """
    qs = (
        ezidapp.models.news_feed.NewsFeed.objects.all()
        .order_by('-published')
        .values(
            'title',
            'link',
        )[:3]
    )
    if qs.exists():
        return [(q['title'], q['link']) for q in qs]
    return NO_NEWS
