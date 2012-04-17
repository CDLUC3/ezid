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

def isUiRequest (request):
  """
  Returns true if the request is to be handled by the UI as opposed to
  the API.  The determination is based on the client's desired content
  type.
  """
  # In its infinite wisdom IE8 does not express a preference for any
  # variety of HTML or XML, so we cheat and return the UI if the
  # request appears to come from a browser.
  return ("HTTP_USER_AGENT" in request.META and\
    "Mozilla" in request.META["HTTP_USER_AGENT"]) or\
    ("HTTP_ACCEPT" in request.META and\
    _htmlWanted(request.META["HTTP_ACCEPT"]))

def d (request, function, ssl=False):
  """
  Dispatches a request to the API or UI depending on the client's
  desired content type.
  
  UI is now in multiple modules, so has namespacing.  API ignores
  modules namespacing, so module name gets ignored and goes to api
  module only.
  """
  if isUiRequest(request):
    return reduce(getattr, function.split(".")[1:],
                  __import__(function.partition(".")[0]))(request)
  else:
    return getattr(api, function.split(".")[1])(request)
