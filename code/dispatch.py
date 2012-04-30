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

def d (request, apiFunction, uiFunction, ssl=False):
  """
  Dispatches a request to the API or UI depending on the client's
  desired content type.  Each function name must be qualified with a
  module name.
  """
  if isUiRequest(request):
    f = uiFunction
  else:
    f = apiFunction
  module, function = f.rsplit(".", 1)
  # The 'ssl' argument need not be passed on, as it is only used by
  # middleware code.
  return getattr(__import__(module, fromlist=module), function)(request)
