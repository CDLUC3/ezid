#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

# Creates a link checker summary report in the form of a CSV file.
# The report lists broken target URL counts broken down by identifier
# owner and by when the target URL was first detected broken.  The
# report is either emailed, written to a named file, or written to
# standard output.
#
# Usage: link-check-summary-report [options]
#
# Options:
#   -a EMAIL  email report to address (may be repeated)
#   -o FILE   output to file
#   -r REALM  restrict to realm
#
# Greg Janee <gjanee@ucop.edu>
# May 2017

import csv
import optparse
import os
import os.path
import sys
import tempfile

import django.conf
import django.core.mail
import django.db.models

# import ezidapp.models
import ezidapp.models.link_checker
import ezidapp.models.realm
import ezidapp.models.user
import impl

BAD_RECHECK_MIN_INTERVAL = int(
    django.conf.settings.LINKCHECKER_BAD_RECHECK_MIN_INTERVAL
)
NOTIFICATION_THRESHOLD = int(django.conf.settings.LINKCHECKER_NOTIFICATION_THRESHOLD)

message = """Dear EZID administrator,

The attached CSV file lists broken target URL counts broken down by
identifier owner and by when the target URL was first detected broken.

Best,
EZID Team

This is an automated email.  Please do not reply.

"""


def main():
    p = optparse.OptionParser(usage="%prog [options]")
    p.add_option(
        "-a",
        metavar="EMAIL",
        action="append",
        dest="emailAddresses",
        default=[],
        help="email report to address (may be repeated)",
    )
    p.add_option(
        "-o", metavar="FILE", action="store", dest="outputFile", help="output to file"
    )
    p.add_option(
        "-r", metavar="REALM", action="store", dest="realm", help="restrict to realm"
    )
    options, args = p.parse_args()
    if len(args) > 0:
        p.error("unexpected argument")
    if len(options.emailAddresses) > 0:
        if any("@" not in a for a in options.emailAddresses):
            p.error("invalid email address")
        if options.outputFile is not None:
            p.error("options -a and -o are incompatible")
        options.email = True
    else:
        options.email = False
    if options.realm:
        if not ezidapp.models.realm.Realm.objects.filter(
            name=options.realm
        ).exists():
            p.error("no such realm")
    # We use the total number of failures as a proxy for age of
    # broken-ness by computing the maximum number of consecutive
    # check failures that can occur in a month.
    fpm = int((30 * 86400.0) / BAD_RECHECK_MIN_INTERVAL)
    # We can't use a join in the query below because the tables aren't
    # related (at least as far as Django is concerned), so we manually
    # create a lookup table.
    users = ezidapp.models.user.User.objects
    if options.realm:
        users = users.filter(realm__name=options.realm)
    else:
        users = users.all()
    users = {su.id: su.username for su in users.only("id", "username")}

    def countExpression(from_, to):
        d = {"then": 1}
        if from_ is not None:
            d["numFailures__gt"] = from_
        if to is not None:
            d["numFailures__lte"] = to
        return django.db.models.Count(django.db.models.Case(django.db.models.When(**d)))

    data = (
        ezidapp.models.link_checker.LinkChecker.objects.filter(
            numFailures__gte=NOTIFICATION_THRESHOLD
        )
        .values("owner_id")
        .annotate(total=django.db.models.Count(1))
        .annotate(age1Month=countExpression(None, fpm))
        .annotate(age2Months=countExpression(fpm, 2 * fpm))
        .annotate(age3Months=countExpression(2 * fpm, 3 * fpm))
        .annotate(older=countExpression(3 * fpm, None))
        .order_by("-total")
    )
    if options.email:
        tempDirectory = tempfile.mkdtemp()
        filename = os.path.join(tempDirectory, "summary_report.csv")
        f = open(filename, "w")
    elif options.outputFile is not None:
        f = open(options.outputFile, "w")
    else:
        f = sys.stdout
    w = csv.writer(f)
    w.writerow(
        [
            "owner",
            "total broken target URLs",
            "1 month old",
            "2 months old",
            "3 months old",
            "older",
        ]
    )
    for r in data:
        if r["owner_id"] in users:
            w.writerow(
                [
                    users[r["owner_id"]],
                    r["total"],
                    r["age1Month"],
                    r["age2Months"],
                    r["age3Months"],
                    r["older"],
                ]
            )
    f.close()
    if options.email:
        m = django.core.mail.EmailMessage(
            subject="EZID link checker summary report",
            body=message,
            from_email=django.conf.settings.SERVER_EMAIL,
            to=options.emailAddresses,
        )
        # noinspection PyUnboundLocalVariable
        m.attach_file(filename)
        m.send()
        try:
            os.unlink(filename)
            # noinspection PyUnboundLocalVariable
            os.rmdir(tempDirectory)
        except Exception:
            pass


if __name__ == "__main__":
    main()
