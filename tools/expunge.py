#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Expunges expired test identifiers

Such identifiers are discovered by querying the database directly, but expunged by
requesting that the (live) EZID server delete them.

This script requires several EZID modules.  The PYTHONPATH environment variable must
include the .../SITE_ROOT/PROJECT_ROOT directory; if it doesn't, we attempt to
dynamically locate it and add it.  The DJANGO_SETTINGS_MODULE environment variable must
be set.
"""

import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.response

import django.conf
import django.db

import ezidapp.models.identifier
import ezidapp.models.shoulder

# from impl # import ezidapp.models

expireTime = int(time.time()) - 14 * 86400
baseUrl = django.conf.settings.EZID_BASE_URL
adminPassword = django.conf.settings.ADMIN_PASSWORD

if len(sys.argv) != 1:
    sys.stderr.write("Usage: expunge\n")
    sys.exit(1)

expungeList = []
for prefix in [
    ezidapp.models.shoulder.getArkTestShoulder().prefix,
    ezidapp.models.shoulder.getDoiTestShoulder().prefix,
    ezidapp.models.shoulder.getCrossrefTestShoulder().prefix,
]:
    expungeList.extend(
        [
            si.identifier
            for si in ezidapp.models.identifier.Identifier.objects.filter(
                identifier__startswith=prefix
            )
            .filter(createTime__lte=expireTime)
            .only("identifier")
        ]
    )

django.db.connections["default"].close()

opener = urllib.request.build_opener()
h = urllib.request.HTTPBasicAuthHandler()
h.add_password("EZID", baseUrl, "admin", adminPassword)
opener.add_handler(h)


def deleteIdentifier(identifier):
    # Though we read identifiers directly from the EZID database, to
    # avoid conflicts with the corresponding running system we don't
    # delete identifiers directly, but ask the system to do so.
    r = urllib.request.Request(
        "%s/id/%s" % (baseUrl, urllib.parse.quote(identifier, ":/"))
    )
    r.get_method = lambda: "DELETE"
    c = None
    try:
        c = opener.open(r)
        s = c.read()
        assert s.startswith("success:"), "unexpected response received: " + s
    # except urllib.error.HTTPError as e:
    #   msg = None
    #   if e.fp is not None :
    #     try:
    #       _m = e.fp.read()
    #     except Exception:
    #       pass
    #   raise urllib.error.HTTPError(url=e.url, code=e.code, msg=msg, fp=e.fp) from e
    finally:
        if c:
            c.close()


for identifier in expungeList:
    try:
        deleteIdentifier(identifier)
    except Exception:
        sys.stderr.write("expunge: processing %s\n" % identifier)
        raise
