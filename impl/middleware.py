#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Request/response middleware
"""

# TODO: We no longer import config here (as it no longer exists). Is the behavior described in this old comment still an issue?
#
# Some things in life are just destined to remain a mystery.  If the
# EZID administrator is logged in and viewing a Django admin page, and
# if the server is restarted and the page refreshed, Django asks the
# user to log in again.  This mildly annoying behavior only happens
# with Django admin pages, no other EZID pages.  But,
# incomprehensibly, it goes away if the 'config' module imported here.
# Why?!

import impl.util


class ExceptionScrubberMiddleware:
    def __init__(self, get_response):
        pass

    def process_exception(self, request, _exception):
        if "HTTP_AUTHORIZATION" in request.META:
            try:
                u, p = impl.util.parse_basic_auth(request.META["HTTP_AUTHORIZATION"])
            except ValueError:
                return
            request.META["HTTP_AUTHORIZATION"] = impl.util.basic_auth(u, '*' * 10)
