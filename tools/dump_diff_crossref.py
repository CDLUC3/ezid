#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Compares EZID DOI metadata (as obtained from an EZID raw dump) with Crossref
<https://crossref.org/> DOI metadata (as obtained from a Crossref system query) and
Handle System <https://dx.doi.org/> target URLs.

Usage: diff-ezid-crossref [options] dumpfile queryfile

Options:
  -p   write progress records to stderr
  -s   skip target URL comparisons
  -r N restart from the Nth identifier (useful if interrupted)

'dumpfile' should be a raw EZID dump. If the filename ends with ".gz", the dump is
assumed to be gzip-compressed. 'queryfile' should be a CSV file obtained from running
'dump-crossref'. Of course, for the comparison to be meaningful the dumpfile and
queryfile must agree in scope and have been obtained contemporaneously.

Only metadata and target URLs for non-reserved, real identifiers are compared. (Only
exported identifiers are compared, but then, all Crossref identifiers are exported.)

LIMITATION/TBD: this script does not properly handle unavailable identifiers. It should
anticipate and check that unavailable identifiers, as well as identifiers in Crossref
but not in EZID, have titles prepended with "WITHDRAWN:" and have the standard invalid
target URL.

This script requires several EZID modules. The PYTHONPATH environment variable must
include the .../SITE_ROOT/PROJECT_ROOT directory; if it doesn't, we attempt to
dynamically locate it and add it. The DJANGO_SETTINGS_MODULE environment variable must
be set.
"""

import base64
import gzip
import optparse
import re
import sys
import time

import ezidapp.models.model_util
from impl import handle_system
from impl import util
from impl import util2

parser = optparse.OptionParser(usage="%prog [options] dumpfile queryfile")
parser.add_option(
    "-p",
    action="store_true",
    dest="printProgress",
    default=False,
    help="write progress records to stderr",
)
parser.add_option(
    "-s",
    action="store_true",
    dest="skipTargetUrls",
    default=None,
    help="skip target URL comparisons",
)
parser.add_option(
    "-r",
    action="store",
    type="int",
    dest="restartFrom",
    default=1,
    help="restart from the Nth identifier (useful if interrupted)",
    metavar="N",
)
options, args = parser.parse_args()
if len(args) != 2:
    parser.error("wrong number of arguments")

if args[0].endswith(".gz"):
    ezidFile = gzip.GzipFile(filename=args[0], mode="r")
else:
    ezidFile = open(args[0])
crossrefFile = open(args[1])


def formatTimestamp(t):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t))


def unpackCrossrefRow(row):
    assert row[-1] == "\n", "queryfile error: no newline"
    # We don't use Python's 'csv' module since we're going to want to
    # track file seek positions below. There can't be a comma in base64
    # encoding, ergo...
    doi, metadata = row.strip().rsplit(",", 1)
    if doi.startswith('"'):
        assert doi.endswith('"'), "queryfile error: quoting anomaly"
        doi = doi[1:-1].replace('""', '"')
    assert len(doi) > 0, "queryfile error: no identifier"
    assert len(metadata) > 0, "queryfile error: no metadata"
    metadata = base64.b64decode(metadata)
    return doi, metadata


def progress(s):
    if options.printProgress:
        sys.stderr.write(s + "\n")
        sys.stderr.flush()
        sys.stdout.flush()


# Pass 1. Index the Crossref queryfile.

progress("pass 1")

crossrefDois = {}

seekPosition = 0
for row in crossrefFile:
    doi, metadata = unpackCrossrefRow(row)
    if not util2.isTestIdentifier(doi):
        assert doi not in crossrefDois, "duplicate identifier in queryfile"
        crossrefDois[doi] = seekPosition
    seekPosition += len(row)

# Pass 2. Compare. After identifiers are processed they are removed
# from 'crossrefDois'.

progress("pass 2")


def compareXml(node1, node2, mismatches):
    # Returns True if two XML element trees have the same structure and
    # same element order; the same attributes and attribute values; and
    # the same textual content. Element namespace, attribute order, and
    # surrounding and interstitial whitespace are allowed to differ.
    # Mismatch pairs (value1, value2) are appended to list 'mismatches'.
    def localName(tag):
        return tag.split("}")[1]

    # Crossref internally normalizes text values.
    def normalize(text):
        return re.sub("\\s+", " ", (text or "").strip())

    if localName(node1.tag) != localName(node2.tag):
        mismatches.append(
            ("...<%s>" % localName(node1.tag), "...<%s>" % localName(node2.tag))
        )
        return False
    if node1.attrib != node2.attrib:
        for k in node1.attrib:
            if k in node2.attrib:
                if node1.attrib[k] != node2.attrib[k]:
                    mismatches.append(
                        (
                            "...<%s %s=\"%s\">"
                            % (localName(node1.tag), k, node1.attrib[k]),
                            "...<%s %s=\"%s\">"
                            % (localName(node2.tag), k, node2.attrib[k]),
                        )
                    )
            else:
                mismatches.append(
                    (
                        "...<%s %s=\"%s\">"
                        % (localName(node1.tag), k, node1.attrib[k]),
                        "...<%s>" % localName(node2.tag),
                    )
                )
        for k in node2.attrib:
            if k not in node1.attrib:
                mismatches.append(
                    (
                        "...<%s>" % localName(node1.tag),
                        "...<%s %s=\"%s\">"
                        % (localName(node2.tag), k, node2.attrib[k]),
                    )
                )
        return False
    if normalize(node1.text) != normalize(node2.text):
        mismatches.append(
            (
                "...<%s>%s" % (localName(node1.tag), normalize(node1.text)),
                "...<%s>%s" % (localName(node2.tag), normalize(node2.text)),
            )
        )
        return False
    if normalize(node1.tail) != normalize(node2.tail):
        mismatches.append(
            (
                "...</%s>%s" % (localName(node1.tag), normalize(node1.tail)),
                "...</%s>%s" % (localName(node2.tag), normalize(node2.tail)),
            )
        )
        return False
    if len(node1) != len(node2):
        mismatches.append(
            (
                "...<%s>: #children=%d" % (localName(node1.tag), len(node1)),
                "...<%s>: #children=%d" % (localName(node2.tag), len(node2)),
            )
        )
        return False
    for c1, c2 in zip(node1.iterchildren(), node2.iterchildren()):
        if not compareXml(c1, c2, mismatches):
            return False
    return True


def toHttps(url):
    if url.startswith("http://ezid.cdlib.org/"):
        return "https" + url[4:]
    else:
        return url


def doComparison(doi, metadata):
    error = ""
    diffs = []
    if doi not in crossrefDois:
        error += ", not in Crossref"
    else:
        ezidMetadata = util.parseXmlString(metadata["crossref"])
        crossrefFile.seek(crossrefDois[doi])
        crMetadata = util.parseXmlString(unpackCrossrefRow(crossrefFile.readline())[1])
        # The metadata comparison is complicated by the fact that Crossref
        # mucks with schema versions and normalizes whitespace. So, we do
        # a structural comparison.
        del ezidMetadata.attrib[
            "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"
        ]
        mismatches = []
        if not compareXml(ezidMetadata, crMetadata, mismatches):
            error += ", metadata mismatch"
            for m in mismatches:
                diffs.append("< crossref: " + m[0])
                diffs.append("> crossref: " + m[1])
    if not options.skipTargetUrls:
        url = handle_system.getRedirect(doi[4:])
        if url is not None:
            if metadata["_status"] == "public":
                if url != metadata["_target"]:
                    error += ", target URL mismatch in Handle System"
                    diffs.append("< _target: " + metadata["_target"])
                    diffs.append("> _target: " + url)
            else:
                # We have to take into account that some older EZID target
                # URLs specify http, not https.
                if toHttps(url) != util2.tombstoneTargetUrl(doi):
                    error += ", has non-tombstone target URL in Handle System"
                    diffs.append("< _target: " + util2.tombstoneTargetUrl(doi))
                    diffs.append("> _target: " + url)
        else:
            error += ", not in Handle System"
    if len(error) > 0:
        if metadata["_status"] == "public":
            status = "public"
        else:
            status = "unavailable"
        print(f"{doi}: in EZID ({status}){error}")
        print("\t< _created: {0}".format(formatTimestamp(int(metadata["_created"]))))
        print("\t< _updated: {0}".format(formatTimestamp(int(metadata["_updated"]))))
        for d in diffs:
            print("\t" + d)


numDois = max(len(crossrefDois), 1)
n = 0
for record in ezidFile:
    id = None
    try:
        id, metadata = util.fromExchange(record, True)
        if not id.startswith("doi:"):
            continue
        if util2.isTestIdentifier(id):
            continue
        ezidapp.models.model_util.convertLegacyToExternal(metadata, False)
        if metadata["_status"] == "reserved":
            continue
        if "_crossref" not in metadata:
            continue
        n += 1
        if n >= options.restartFrom:
            if n % 1000 == 0:
                progress("%d (%d%%)" % (n, int(float(n * 100) / numDois)))
            doComparison(id, metadata)
        if id in crossrefDois:
            del crossrefDois[id]
    except Exception as e:
        print("exception while processing %s: %s" % (id, util.formatException(e)))
        raise

# Pass 3. There shouldn't be any identifiers remaining in
# 'crossrefDois'.

progress("pass 3")

for doi in crossrefDois:
    # The following check is insufficient; it should include a check
    # that the title(s) are prepended with "WITHDRAWN:".
    if handle_system.getRedirect(doi[4:]) != "http://datacite.org/invalidDOI":
        print(f"{doi}: in Crossref, not in EZID")
