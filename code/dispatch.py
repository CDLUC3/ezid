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

def d (request, ui_function, api_function, ssl=False):
  """
  Dispatches a request to the API or UI functiondepending on the client's
  desired content type.  Module and function name are now passed in
  with those parameters and namespaced with module names like
  {'ui_function': 'ui_catfood.meow', 'api_function': 'api.meow_meow_meow'}
  """
  if isUiRequest(request):
    my_func = ui_function
  else:
    my_func = api_function
  return reduce(getattr, my_func.split(".")[1:],
                  __import__(my_func.partition(".")[0]))(request)
