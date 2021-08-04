_NO_NEWS = [("No news available", None)]
_ITEMS = _NO_NEWS


def getLatestItems(self):
    """Returns the latest news items (up to 3 items) as a list of tuples.

    [(title, URL), ...].  At least one item is always returned.  The URL
    may be None in a tuple.
    """
    return self._ITEMS
