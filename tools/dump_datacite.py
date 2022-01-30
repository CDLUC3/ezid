#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""
Dumps DOIs belonging to one or more DataCite datacenters to standard output.

Usage: dump-datacite datacenter...

The output format is CSV with three columns: identifier (in qualified, normalized form),
datacenter symbol (e.g., "CDL.CDL"), and Base64-encoded DataCite XML metadata.

DataCite currently returns public, exported DOIs only. Unavailable and unexported
identifiers are marked as inactive in DataCite, and as a result are not returned (and
reserved identifiers are not registered with DataCite at all).

This script requires an EZID module. The PYTHONPATH environment variable must include
the .../SITE_ROOT/PROJECT_ROOT/impl directory; if it doesn't, we attempt to dynamically
locate it and add it.
"""
import csv
import json
import sys
import urllib.parse
import urllib.request
import urllib.response

import impl.util

listTemplate = (
    "https://api.datacite.org/dois?client-id=%s" + "&page[size]=1000&page[cursor]=1"
)
doiTemplate = "https://api.datacite.org/dois/%s"

w = csv.writer(sys.stdout)

for datacenter in sys.argv[1:]:
    link = listTemplate % datacenter.lower()
    while link is not None:
        j = json.loads(urllib.request.urlopen(link).read())
        for r in j["data"]:
            doi = r["attributes"]["doi"]
            id = "doi:" + impl.util.validateDoi(doi)
            jj = json.loads(
                urllib.request.urlopen(doiTemplate % urllib.parse.quote(doi)).read()
            )
            w.writerow([id, datacenter, jj["data"]["attributes"]["xml"]])
        link = j["links"].get("next")
