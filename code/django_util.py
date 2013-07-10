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

def deleteSessions (username):
  """
  Deletes all sessions for a given user.
  """
  # Force instantiation of query set to limit database contention.
  sessions = django.contrib.sessions.models.Session.objects.all()
  for s in sessions:
    d = s.get_decoded()
    if "auth" in d and d["auth"].user[0] == username: s.delete()
