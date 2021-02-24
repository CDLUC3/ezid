#! /usr/bin/env python

# Compares EZID DOI metadata (as obtained from an EZID raw dump) with
# DataCite <https://datacite.org/> DOI metadata (as obtained from a
# DataCite search system query) and Handle System
# <https://dx.doi.org/> target URLs.  Only target URLs for
# non-reserved, non-test identifiers are compared; and only metadata
# for public, exported, non-test identifiers is compared.
#
# Usage: diff-ezid-datacite [options] dumpfile queryfile
#
# Options:
#   -p   write progress records to stderr
#   -s   skip target URL comparisons
#   -r N restart from the Nth identifier (useful if interrupted)
#
# 'dumpfile' should be a raw EZID dump.  If the filename ends with
# ".gz", the dump is assumed to be gzip-compressed.
#
# 'queryfile' should be a CSV file obtained from running
# 'dump-datacite'.
#
# The EZID dump and DataCite query must match in terms of scope.  If
# the dump represents all identifiers in EZID, then the query should
# retrieve identifiers for all allocators and datacenters in DataCite
# that are under EZID's control.
#
# This script requires several EZID modules.  The PYTHONPATH
# environment variable must include the .../SITE_ROOT/PROJECT_ROOT
# directory; if it doesn't, we attempt to dynamically locate it and
# add it.  The DJANGO_SETTINGS_MODULE environment variable must be
# set.
#
# Greg Janee <gjanee@ucop.edu>
# November 2014

import base64
import gzip
import optparse
import sys
import time

import lxml.etree

import ezidapp.models.model_util
from impl import datacite
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
mdsFile = open(args[1])


def formatTimestamp(t):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t))


def unpackMdsRow(row):
    assert row[-1] == "\n", "queryfile error: no newline"
    # We don't use Python's 'csv' module since we're going to want to
    # track file seek positions below.  There can't be a comma in base64
    # encoding or in a datacenter name, ergo...
    doi, datacenter, metadata = row.strip().rsplit(",", 2)
    if doi.startswith('"'):
        assert doi.endswith('"'), "queryfile error: quoting anomaly"
        doi = doi[1:-1].replace('""', '"')
    assert len(doi) > 0, "queryfile error: no identifier"
    assert len(datacenter) > 0, "queryfile error: no datacenter"
    assert len(metadata) > 0, "queryfile error: no metadata"
    metadata = base64.b64decode(metadata).decode("UTF-8")
    return doi, datacenter, metadata


def progress(s):
    if options.printProgress:
        sys.stderr.write(s + "\n")
        sys.stderr.flush()
        sys.stdout.flush()


# Pass 1.  Index the MDS queryfile.

progress("pass 1")

mdsDois = {}

seekPosition = 0
for row in mdsFile:
    doi, datacenter, metadata = unpackMdsRow(row)
    if not util2.isTestIdentifier(doi):
        assert doi not in mdsDois, "duplicate identifier in queryfile"
        mdsDois[doi] = seekPosition
    seekPosition += len(row)

# Pass 2.  Compare.  After identifiers are processed they are removed
# from 'mdsDois'.

progress("pass 2")


def compareXml(node1, node2):
    # Returns True if two XML element trees have the same structure and
    # same element order; the same attributes and attribute values; and
    # the same textual content.  Attribute order and surrounding and
    # interstitial whitespace are allowed to differ.
    if node1.tag != node2.tag:
        return False
    if node1.attrib != node2.attrib:
        return False
    if (node1.text or "").strip() != (node2.text or "").strip():
        return False
    if (node1.tail or "").strip() != (node2.tail or "").strip():
        return False
    if len(node1) != len(node2):
        return False
    for c1, c2 in zip(node1.iterchildren(), node2.iterchildren()):
        if not compareXml(c1, c2):
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
    if metadata["_status"] == "public" and metadata["_export"] == "yes":
        if doi not in mdsDois:
            error += ", not in DataCite"
        else:
            mdsFile.seek(mdsDois[doi])
            mdsDatacenter, mdsMetadata = unpackMdsRow(mdsFile.readline())[1:3]
            if mdsDatacenter != metadata["_datacenter"]:
                error += ", datacenter mismatch"
                diffs.append("< _datacenter: " + metadata["_datacenter"])
                diffs.append("> _datacenter: " + mdsDatacenter)
            # The metadata comparison is complicated by the fact that
            # different versions of the DataCite XML schema have been used
            # over time.  And even converting to the latest version, a
            # straight text comparison gets fooled by insignificant
            # differences in namespace prefixes and whitespace.  So, we do a
            # structural comparison.
            ezidMetadata = datacite.upgradeDcmsRecord(
                datacite.formRecord(doi, metadata), returnString=False
            )
            mdsMetadata = datacite.upgradeDcmsRecord(mdsMetadata, returnString=False)
            if not compareXml(ezidMetadata, mdsMetadata):
                error += ", metadata mismatch"
                diffs.append(
                    "< _datacite: "
                    + util.encode1(
                        lxml.etree.tostring(ezidMetadata, encoding="unicode")
                    )
                )
                diffs.append(
                    "> _datacite: "
                    + util.encode1(lxml.etree.tostring(mdsMetadata, encoding="unicode"))
                )
    if not options.skipTargetUrls:
        url = handle_system.getRedirect(doi[4:])
        if url is not None:
            if metadata["_status"] == "public":
                if url != metadata["_target"]:
                    error += ", target URL mismatch in Handle System"
                    diffs.append("< _target: " + util.encode1(metadata["_target"]))
                    diffs.append("> _target: " + util.encode1(url))
            else:
                # We have to take into account that some older EZID target
                # URLs specify http, not https.
                if toHttps(url) != util2.tombstoneTargetUrl(doi):
                    error += ", has non-tombstone target URL in Handle System"
                    diffs.append(
                        "< _target: " + util.encode1(util2.tombstoneTargetUrl(doi))
                    )
                    diffs.append("> _target: " + util.encode1(url))
        else:
            error += ", not in Handle System"
    if len(error) > 0:
        if metadata["_status"] == "public":
            status = "public,%s exported" % (
                "" if metadata["_export"] == "yes" else " not"
            )
        else:
            status = "unavailable"
        print(f"{doi}: in EZID ({status}){error}")
        print("\t< _created: {0}".format(formatTimestamp(int(metadata["_created"]))))
        print("\t< _updated: {0}".format(formatTimestamp(int(metadata["_updated"]))))
        for d in diffs:
            print("\t{0}".format(d))


numDois = max(len(mdsDois), 1)
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
        n += 1
        if n >= options.restartFrom:
            if n % 1000 == 0:
                progress("%d (%d%%)" % (n, int(float(n * 100) / numDois)))
            doComparison(id, metadata)
        if id in mdsDois:
            del mdsDois[id]
    except Exception as e:
        print(f"exception while processing {id}: {util.formatException(e)}")

# Pass 3.  There shouldn't be any identifiers remaining in 'mdsDois'.

progress("pass 3")

for doi in mdsDois:
    print(f"{doi}: in DataCite, not in EZID")
