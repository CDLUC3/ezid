# =============================================================================
#
# EZID :: dispatch.py
#
# Request dispatcher.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2010, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import api
import ui

def _htmlWanted (acceptHeader):
  for mt in acceptHeader.split(","):
    if mt.split(";")[0].strip() in ["text/html", "application/xml",
      "application/xhtml+xml"]:
      return True
  return False

def d (request, function):
  """
  Dispatches a request to the API or UI depending on the client's
  desired content type.
  """
  # In its infinite wisdom IE8 does not express a preference for any
  # variety of HTML or XML, so we cheat and return the UI if the
  # request appears to come from a browser.
  if ("HTTP_USER_AGENT" in request.META and\
    "Mozilla" in request.META["HTTP_USER_AGENT"]) or\
    ("HTTP_ACCEPT" in request.META and\
    _htmlWanted(request.META["HTTP_ACCEPT"])):
    return getattr(ui, function)(request)
  else:
    return getattr(api, function)(request)
