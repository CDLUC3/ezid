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
import django.conf
import django.http
import django.template
import django.template.loader

import dispatch

def _methodNotAllowed ():
  return django.http.HttpResponse(
    django.template.loader.get_template("405.html").render(
      django.template.Context()),
    status=405)

def _isUiRequest (request, view_func):
  return view_func.__module__.startswith("ui") or\
    (view_func.__module__ == "dispatch" and dispatch.isUiRequest(request))

class SslMiddleware:
  """
  Forces SSL usage on selected URLs, and forces non-SSL usage on other
  URLs.  A URL is selected for SSL usage by adding an 'ssl' keyword
  argument to its entry in urls.py.  The "forcing" here is done by
  redirects on GET requests; other request methods are either
  disallowed (if the request does not use SSL but the URL requires it)
  or silently allowed (vice versa).  Note that this processing applies
  only to non-AJAX UI requests, not API requests, and only if the SSL
  Django setting is true.
  """
  def process_view (self, request, view_func, view_args, view_kwargs):
    if not django.conf.settings.SSL: return None
    if request.is_ajax() or not _isUiRequest(request, view_func): return None
    if view_kwargs.get("ssl", False):
      if request.is_secure(): return None
      if request.method == "GET":
        u = request.build_absolute_uri()
        assert u.startswith("http://")
        return django.http.HttpResponseRedirect("https" + u[4:])
      else:
        return _methodNotAllowed()
    else:
      if request.is_secure() and request.method == "GET":
        u = request.build_absolute_uri()
        assert u.startswith("https://")
        return django.http.HttpResponseRedirect("http" + u[5:])
      else:
        return None

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
