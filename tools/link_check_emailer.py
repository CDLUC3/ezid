#! /usr/bin/env python

# Emails link checker reports to all owners of identifiers whose check
# failures have reached the notification threshold.
#
# Usage: link-check-emailer [options]
#
# Options:
#   -a EMAIL  override the account email address (one owner only)
#   -b        bcc realm administrators
#   -f FILE   don't email, just write CSV file (one owner only)
#   -o OWNER  process the specified owner only; may be repeated
#   -t N      override the configured notification threshold
#
# Greg Janee <gjanee@ucop.edu>
# October 2016
import django.conf
import csv
import http
import optparse
import os
import re
import subprocess
import tempfile

import django.conf
import django.core.exceptions
import django.core.mail

# import ezidapp.models
import ezidapp.models.link_checker
import ezidapp.models.identifier
import ezidapp.models.user
import ezidapp.models.user
from impl import config
from impl import util


def encode(s):
    # There seems to be no way to safely encode a multi-line value in CSV.
    return re.sub("\s", " ", s).encode("UTF-8")


def gatherFailures(owner_id, threshold):
    lcList = list(
        ezidapp.models.link_checker.LinkChecker.objects.filter(
            owner_id=owner_id, numFailures__gte=threshold
        )
    )
    i = 0
    while i < len(lcList):
        # We query for the identifier in the main EZID tables to get extra
        # metadata and to confirm that the identifier still exists and is
        # still subject to link checking.
        try:
            si = ezidapp.models.identifier.SearchIdentifier.objects.get(
                identifier=lcList[i].identifier
            )
            if (
                si.isPublic
                and si.owner_id == lcList[i].owner_id
                and si.target == lcList[i].target
            ):
                lcList[i].aux = si
                i += 1
            else:
                del lcList[i]
        except ezidapp.models.identifier.SearchIdentifier.DoesNotExist:
            del lcList[i]
    return lcList


def formatError(returnCode, error):
    if returnCode >= 0:
        if returnCode in http.HTTPStatus.responses:
            return "%d %s" % (returnCode, http.HTTPStatus.responses[returnCode])
        else:
            return "HTTP status code %d" % returnCode
    else:
        return error


def writeCsv(lcList, filename):
    f = open(filename, "w")
    w = csv.writer(f)
    w.writerow(
        [
            "identifier",
            "target URL",
            "failure count",
            "last check time",
            "error",
            "resource creator",
            "resource title",
            "resource publisher",
            "resource date",
            "resource type",
        ]
    )
    for lc in lcList:
        w.writerow(
            [
                lc.identifier,
                encode(lc.target),
                str(lc.numFailures),
                util.formatTimestampZulu(lc.lastCheckTime),
                encode(formatError(lc.returnCode, lc.error)),
                encode(lc.aux.resourceCreator),
                encode(lc.aux.resourceTitle),
                encode(lc.aux.resourcePublisher),
                encode(lc.aux.resourcePublicationDate),
                encode(lc.aux.resourceType),
            ]
        )
    f.close()


def compressCsv(csvFilename, zipFilename):
    p = subprocess.Popen(
        [django.conf.settings.ZIP_COMMAND, "-jq", zipFilename, csvFilename],
        close_fds=True,
        env={},
    )
    p.communicate()
    assert p.returncode == 0, "ZIP command failed"


template = """Dear EZID user "%s",

You are receiving this message because the EZID link checker has
discovered that %d of your identifiers have broken target URLs
(also referred to as object locations).  A broken target URL is
one that has failed to load for at least two weeks.  Attached to
this message is a ZIP-compressed, Excel-compatible CSV file
listing the identifiers in question, their target URLs, and
other pertinent information.

There are many reasons a target URL may be broken.  The
identified object may have moved, in which case the identifier
needs to be updated.  Or there may be a problem with the server
hosting the URL.  If an object is no longer available, the
identifier's status can and should be set to "unavailable" using
EZID's UI or API.

Best,
EZID Team

This is an automated email.  Please do not reply.

"""


def emailReport(username, numFailures, accountEmail, bccEmails, zipFilename):
    m = django.core.mail.EmailMessage(
        subject="monthly EZID link checker report",
        body=template % (username, numFailures),
        from_email=django.conf.settings.SERVER_EMAIL,
        to=[accountEmail],
        bcc=bccEmails,
    )
    m.attach_file(zipFilename)
    m.send()


def process1(username, owner_id, accountEmail, bccEmails, threshold, filename):
    # If a filename is supplied, no email is sent and that file is
    # written, even if there are no failures to report.  Otherwise, an
    # email is sent only if there are failures to report.
    lcList = gatherFailures(owner_id, threshold)
    if filename is not None:
        writeCsv(lcList, filename)
    else:
        if len(lcList) > 0:
            d = tempfile.mkdtemp()
            try:
                csvFilename = os.path.join(d, "bad_links.csv")
                zipFilename = os.path.join(d, "bad_links.zip")
                writeCsv(lcList, csvFilename)
                compressCsv(csvFilename, zipFilename)
                emailReport(username, len(lcList), accountEmail, bccEmails, zipFilename)
            finally:
                try:
                    # noinspection PyUnboundLocalVariable
                    os.unlink(csvFilename)
                except Exception:
                    pass
                try:
                    # noinspection PyUnboundLocalVariable
                    os.unlink(zipFilename)
                except Exception:
                    pass
                try:
                    os.rmdir(d)
                except Exception:
                    pass


def main():
    p = optparse.OptionParser(usage="%prog [options]")
    p.add_option(
        "-a",
        metavar="EMAIL",
        action="store",
        dest="emailAddress",
        help="override the account email address (one owner only)",
    )
    p.add_option(
        "-b",
        action="store_true",
        dest="bccRealmAdmins",
        help="bcc realm administrators",
        default=False,
    )
    p.add_option(
        "-f",
        metavar="FILE",
        action="store",
        dest="outputFile",
        help="don't email, just write CSV file (one owner only)",
    )
    p.add_option(
        "-o",
        metavar="OWNER",
        action="append",
        dest="owners",
        default=[],
        help="process the specified owner only; may be repeated",
    )
    p.add_option(
        "-t",
        metavar="N",
        action="store",
        type="int",
        dest="threshold",
        help="override the configured notification threshold",
        default=int(django.conf.settings.LINKCHECKER_NOTIFICATION_THRESHOLD),
    )
    options, args = p.parse_args()
    if len(args) > 0:
        p.error("unexpected argument")
    if options.threshold <= 0:
        p.error("-t must be positive")
    if options.outputFile is not None and len(options.owners) != 1:
        p.error("-f requires single -o option")
    if options.emailAddress is not None and len(options.owners) != 1:
        p.error("-a requires single -o option")
    if len(options.owners) > 0:
        for i in range(len(options.owners)):
            username = options.owners[i]
            try:
                su = ezidapp.models.user.SearchUser.objects.get(username=username)
                options.owners[i] = (
                    username,
                    su.id,
                    su.realm.name,
                    ezidapp.models.user.StoreUser.StoreUser.objects.get(
                        username=username
                    ).accountEmail,
                )
            except django.core.exceptions.ObjectDoesNotExist:
                p.error("no such user: {} {} {} {}".format(*username))
    else:
        emailAddresses = {
            su.username: su.accountEmail
            for su in ezidapp.models.user.StoreUser.objects.all()
        }
        options.owners = [
            (su.username, su.id, su.realm.name, emailAddresses[su.username])
            for su in ezidapp.models.user.SearchUser.objects.all()
        ]
    realmAdmins = {}
    if options.bccRealmAdmins:
        for su in ezidapp.models.user.StoreUser.objects.filter(
            isRealmAdministrator=True
        ):
            l = realmAdmins.get(su.realm.name, [])
            l.append(su.accountEmail)
            realmAdmins[su.realm.name] = l
    for username, owner_id, realm, accountEmail in options.owners:
        process1(
            username,
            owner_id,
            options.emailAddress if options.emailAddress is not None else accountEmail,
            realmAdmins.get(realm, []),
            options.threshold,
            options.outputFile,
        )


if __name__ == "__main__":
    main()
