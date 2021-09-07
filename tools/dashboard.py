#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

# Computes cumulative EZID statistics and uploads them to the CDL
# dashboard service.
#
# The statistics consist of cumulative identifier counts aggregated by
# month and broken down by identifier type (UUIDs are not currently
# included).  The counts do not include test identifiers, but do
# include reserved identifiers.  Example data:
#
#   YYYY-MM,DOI,ARK
#   2010-06,1,0
#   2010-07,44,0
#   2010-08,134,0
#   2010-09,1162,15
#   2010-10,1199,59
#   2010-11,1296,43089
#   ...
#
# Usage:
#
#   dashboard dashurl
#   dashboard --compute-only > data
#   dashboard --upload-only dashurl < data
#
#     dashurl: dashboard base URL (http[s]://host:port)
#
# This script requires several EZID modules.  The PYTHONPATH
# environment variable must include the .../SITE_ROOT/PROJECT_ROOT
# directory; if it doesn't, we attempt to dynamically locate it and
# add it.  The DJANGO_SETTINGS_MODULE environment variable must be
# set.
#
# Greg Janee <gjanee@ucop.edu>
# November 2011

import datetime
import re
import sys
import urllib.request

# import urllib2
import uuid

# import ezidapp.models
import ezidapp.models.identifier

usageText = """Usage:

  dashboard dashurl
  dashboard --compute-only > data
  dashboard --upload-only dashurl < data

    dashurl: dashboard base URL (http[s]://host:port)
"""

if len(sys.argv) == 2 and re.match("https?://", sys.argv[1]):
    doCompute = doUpload = True
    dashUrl = sys.argv[1]
elif len(sys.argv) == 2 and sys.argv[1] == "--compute-only":
    doCompute = True
    doUpload = False
elif (
    len(sys.argv) == 3
    and sys.argv[1] == "--upload-only"
    and re.match("https?://", sys.argv[2])
):
    doCompute = False
    doUpload = True
    dashUrl = sys.argv[2]
else:
    sys.stderr.write(usageText)
    sys.exit(1)

if doUpload:
    # noinspection PyUnboundLocalVariable
    slash = "" if dashUrl.endswith("/") else "/"
    uploadUrl = "%s%scgi-bin/file_upload.cgi" % (dashUrl, slash)
    uploadCompletionUrl = "%s%scgi-bin/file_upload_completion.cgi" % (dashUrl, slash)


class Counter(object):
    def __init__(self):
        self.numArks = 0
        self.numDois = 0
        self.numUuids = 0

    def __str__(self):
        # UUID counts are not included yet.
        return "%d,%d" % (self.numDois, self.numArks)

    def __iadd__(self, other):
        self.numArks += other.numArks
        self.numDois += other.numDois
        self.numUuids += other.numUuids
        return self


def incrementMonth(month):
    return (month + datetime.timedelta(31)).replace(day=1)


if doCompute:
    # Gather raw counts.
    counters = {}
    lastIdentifier = ""
    while True:
        qs = (
            ezidapp.models.identifier.Identifier.objects.filter(
                identifier__gt=lastIdentifier
            )
            .only("identifier", "createTime", "isTest")
            .order_by("identifier")
        )
        qs = list(qs[:1000])
        if len(qs) == 0:
            break
        for id in qs:
            if not id.isTest:
                month = datetime.date.fromtimestamp(id.createTime).replace(day=1)
                if month in counters:
                    c = counters[month]
                else:
                    c = Counter()
                    counters[month] = c
                if id.isArk:
                    c.numArks += 1
                elif id.isDoi:
                    c.numDois += 1
                elif id.isUuid:
                    c.numUuids += 1
                else:
                    assert False, "unhandled case"
        lastIdentifier = qs[-1].identifier
    # Fill in any missing months.
    months = list(sorted(counters.keys()))
    for month in months:
        if month != months[0]:
            # noinspection PyUnboundLocalVariable
            nextMonth = incrementMonth(lastMonth)
            while nextMonth not in months:
                counters[nextMonth] = Counter()
                nextMonth = incrementMonth(nextMonth)
        lastMonth = month
    # Accumulate counts, excluding the current month (which is partial).
    thisMonth = datetime.date.today().replace(day=1)
    data = "YYYY-MM,DOI,ARK\n"
    months = list(sorted(counters.keys()))
    lastMonth = Counter()
    lastDataMonth = None
    for month in months:
        counters[month] += lastMonth
        if month < thisMonth:
            data += "%s,%s\n" % (month.isoformat()[:7], counters[month])
            lastDataMonth = month
        lastMonth = counters[month]
    if lastDataMonth is None and doUpload:
        sys.stderr.write("dashboard: insufficient data to upload\n")
        sys.exit(1)
else:
    # Load previously-generated data.
    data = sys.stdin.read()
    m = data.splitlines()[-1].split(",")[0]
    if m == "YYYY-MM":
        sys.stderr.write("dashboard: insufficient data to upload\n")
        sys.exit(1)
    lastDataMonth = datetime.date(int(m[:4]), int(m[5:]), 1)

boundary = "BOUNDARY_" + uuid.uuid1().hex


def multipartBody(*parts):
    body = []
    for p in parts:
        body.append("--" + boundary)
        if len(p) == 2:
            body.append("Content-Disposition: form-data; name=\"%s\"" % p[0])
            body.append("")
            body.append(p[1])
        else:
            body.append(
                ("Content-Disposition: form-data; name=\"%s\"; " + "filename=\"%s\"")
                % (p[0], p[1])
            )
            body.append("Content-Type: text/plain")
            body.append("")
            body.append(p[2])
    body.append("--%s--" % boundary)
    return "\r\n".join(body)


if doUpload:
    year = "%02d" % (lastDataMonth.year % 100)
    month = "%02d" % lastDataMonth.month
    body = multipartBody(
        ("typefile", "IdentifiersEZID"),
        ("year", year),
        ("month", month),
        ("filename", "IdentifiersEZID%s%s.csv" % (year, month), data),
    )
    # noinspection PyUnboundLocalVariable
    response = urllib.request.urlopen(
        urllib.request.Request(
            uploadUrl,
            body.encode('utf-8'),
            {"Content-Type": "multipart/form-data; boundary=" + boundary},
        )
    ).read()
    assert re.search("copy file into production", response, re.I)
    body = multipartBody(
        ("typefile", "IdentifiersEZID"), ("year", year), ("month", month)
    )
    # noinspection PyUnboundLocalVariable
    response = urllib.request.urlopen(
        urllib.request.Request(
            uploadCompletionUrl,
            body.encode('utf-8'),
            {"Content-Type": "multipart/form-data; boundary=" + boundary},
        )
    ).read()
    assert re.search("your file is now moved", response, re.I)
else:
    sys.stdout.write(data)
