#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

# Dumps all DOIs under one or more Crossref prefixes to standard
# output.  10.20354 is an example of a prefix.
#
# Usage: dump-crossref prefix...
#
# The output format is CSV with two columns: identifier (in qualified,
# normalized form) and Base64-encoded Crossref deposit XML metadata.
#
# Reserved identifiers are not registered with Crossref, and
# hence will not be returned.
#
# This script requires an EZID module.  The PYTHONPATH environment
# variable must include the .../SITE_ROOT/PROJECT_ROOT/impl directory;
# if it doesn't, we attempt to dynamically locate it and add it.
#
# Greg Janee <gjanee@ucop.edu>
# July 2019

import base64
import csv
import json
import sys
import urllib.parse
import urllib.request
import urllib.response

import lxml.etree

import impl.util

listTemplate = "https://api.crossref.org/prefixes/%s/works?cursor=%s&select=DOI"
metadataTemplate = (
    "https://api.crossref.org/"
    + "works/%s/transform/application/vnd.crossref.unixsd+xml"
)
headers = {"User-Agent": "EZID (https://ezid.cdlib.org; mailto:ezid@ucop.edu)"}

writer = csv.writer(sys.stdout)

for prefix in sys.argv[1:]:
    cursor = "*"
    while True:
        c = urllib.request.urlopen(
            urllib.request.Request(
                listTemplate % (prefix, urllib.parse.quote_plus(cursor)),
                headers=headers,
            )
        )
        j = json.loads(c.read())
        c.close()
        assert j["status"] == "ok"
        if len(j["message"]["items"]) == 0:
            break
        for doi in [i["DOI"] for i in j["message"]["items"]]:
            c = urllib.request.urlopen(
                urllib.request.Request(metadataTemplate % doi, headers=headers)
            )
            metadata = c.read()
            c.close()
            root = lxml.etree.XML(metadata)
            assert root.tag == "{http://www.crossref.org/qrschema/3.0}crossref_result"
            l = root.xpath(
                "//N:crossref", namespaces={"N": "http://www.crossref.org/xschema/1.1"}
            )
            assert len(l) == 1
            crossrefNode = l[0]
            assert len(crossrefNode) == 1  # i.e., has one child node
            writer.writerow(
                [
                    "doi:" + impl.util.validateDoi(doi),
                    base64.b64encode(lxml.etree.tostring(crossrefNode[0])),
                ]
            )
        cursor = j["message"]["next-cursor"]
