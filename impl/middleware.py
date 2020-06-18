# =============================================================================
#
# EZID :: middleware.py
#
# Request/response middleware.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2010, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import base64

# Some things in life are just destined to remain a mystery.  If the
# EZID administrator is logged in and viewing a Django admin page, and
# if the server is restarted and the page refreshed, Django asks the
# user to log in again.  This mildly annoying behavior only happens
# with Django admin pages, no other EZID pages.  But,
# incomprehensibly, it goes away if the 'config' module imported here.
# Why?!

import config

class ExceptionScrubberMiddleware:
  def process_exception (self, request, exception):
    if "HTTP_AUTHORIZATION" in request.META:
      try:
        h = request.META["HTTP_AUTHORIZATION"].split()
        assert len(h) == 2 and h[0] == "Basic"
        s = base64.decodestring(h[1])
        assert ":" in s
        s = "Basic base64{%s:********}" % s.split(":", 1)[0]
      except:
        s = "********"
      request.META["HTTP_AUTHORIZATION"] = s
