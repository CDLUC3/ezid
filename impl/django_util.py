# =============================================================================
#
# EZID :: django_util.py
#
# Django utilities.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2013, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.contrib.sessions.models


def deleteSessions(username):
    """Deletes all sessions for a given user.

    The number of sessions deleted is returned.
    """
    toDelete = []
    sessions = django.contrib.sessions.models.Session.objects.all()
    for s in sessions:
        d = s.get_decoded()
        if "auth" in d and d["auth"].user[0] == username:
            toDelete.append(s.pk)
    # We'll hit an SQLite limit if we try to delete too many at once.
    n = len(toDelete)
    while len(toDelete) > 0:
        sessions.filter(pk__in=toDelete[:900]).delete()
        toDelete = toDelete[900:]
    return n
