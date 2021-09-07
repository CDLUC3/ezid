#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

# Reads EZID transaction log files, consolidates transaction BEGIN and
# END records, and filters transactions as specified by command line
# options.  If no files are specified, records are read from standard
# input.
#
# Usage: filterlog [options] files...
#
# Options:
#
#     -v            print transaction IDs
#     -w            print transaction progress records
#     -x            print transaction elapsed times
#
#   User print options:
#     -0            print no user information (default: print all)
#     -1            print username
#     -2            print user agent PID
#     -3            print groupname
#     -4            print group agent PID
#
#   Restrict range of transaction end times:
#     -f TIMESTAMP  from (inclusive; any timestamp prefix)
#     -t TIMESTAMP  to (exclusive)
#
#   Filter by user:
#     -u USER       user
#     -g GROUP      group
#
#   Filter by identifier type:
#     -R            real identifier
#     -T            test identifier
#
#   Filter by operation:
#     -M            mint identifier
#     -C            create identifier
#     -G            get metadata
#     -S            set metadata
#     -D            delete identifier
#     -X            search
#
#   Filter by operation status:
#     -s            success
#     -b            bad request or forbidden
#     -e            internal server error (transactional or other)
#     -p            partial transaction
#
# By default, all records are output.  Filter options are AND'd
# together, but multiple options within an option group are OR'd.
#
# This script requires an EZID module.  The PYTHONPATH environment
# variable must include the .../SITE_ROOT/PROJECT_ROOT directory; if
# it doesn't, we attempt to dynamically locate it and add it.  The
# DJANGO_SETTINGS_MODULE environment variable must be set.
#
# Implementation note: beyond the documentation in log.py, this
# program relies on the fact that BEGIN records currently have the
# following common structure (after the BEGIN keyword):
#
# function identifier username userPid groupname groupPid ...
#
# Greg Janee <gjanee@ucop.edu>
# January 2012

import calendar
import optparse
import re
import sys
import time

from impl import util2

p = optparse.OptionParser(usage="%prog [options] files...")
p.add_option(
    "-v",
    action="store_true",
    dest="printTids",
    default=False,
    help="print transaction IDs",
)
p.add_option(
    "-w",
    action="store_true",
    dest="printProgressRecords",
    default=False,
    help="print transaction progress records",
)
p.add_option(
    "-x",
    action="store_true",
    dest="printElapsedTimes",
    default=False,
    help="print transaction elapsed times",
)
g = optparse.OptionGroup(p, "User print options")
g.add_option(
    "-0",
    action="append_const",
    dest="userAttrs",
    const=0,
    help="print no user information (default: print all)",
)
g.add_option(
    "-1", action="append_const", dest="userAttrs", const=1, help="print username"
)
g.add_option(
    "-2", action="append_const", dest="userAttrs", const=2, help="print user agent PID"
)
g.add_option(
    "-3", action="append_const", dest="userAttrs", const=3, help="print groupname"
)
g.add_option(
    "-4", action="append_const", dest="userAttrs", const=4, help="print group agent PID"
)
p.add_option_group(g)
g = optparse.OptionGroup(p, "Restrict range of transaction end times")
g.add_option(
    "-f",
    action="store",
    type="string",
    dest="from_",
    help="from (inclusive; any timestamp prefix)",
    metavar="TIMESTAMP",
)
g.add_option(
    "-t",
    action="store",
    type="string",
    dest="to",
    help="to (exclusive)",
    metavar="TIMESTAMP",
)
p.add_option_group(g)
g = optparse.OptionGroup(p, "Filter by user")
g.add_option(
    "-u", action="append", type="string", dest="users", help="user", metavar="USER"
)
g.add_option(
    "-g", action="append", type="string", dest="groups", help="group", metavar="GROUP"
)
p.add_option_group(g)
g = optparse.OptionGroup(p, "Filter by identifier type")
g.add_option(
    "-R", action="store_true", dest="typeReal", default=False, help="real identifier"
)
g.add_option(
    "-T", action="store_true", dest="typeTest", default=False, help="test identifier"
)
p.add_option_group(g)
g = optparse.OptionGroup(p, "Filter by operation")
g.add_option(
    "-M",
    action="store_true",
    dest="operationMint",
    default=False,
    help="mint identifier",
)
g.add_option(
    "-C",
    action="store_true",
    dest="operationCreate",
    default=False,
    help="create identifier",
)
g.add_option(
    "-G", action="store_true", dest="operationGet", default=False, help="get metadata"
)
g.add_option(
    "-S", action="store_true", dest="operationSet", default=False, help="set metadata"
)
g.add_option(
    "-D",
    action="store_true",
    dest="operationDelete",
    default=False,
    help="delete identifier",
)
g.add_option(
    "-X", action="store_true", dest="operationSearch", default=False, help="search"
)
p.add_option_group(g)
g = optparse.OptionGroup(p, "Filter by operation status")
g.add_option(
    "-s", action="store_true", dest="statusSuccess", default=False, help="success"
)
g.add_option(
    "-b",
    action="store_true",
    dest="statusBadRequest",
    default=False,
    help="bad request or forbidden",
)
g.add_option(
    "-e",
    action="store_true",
    dest="statusError",
    default=False,
    help="internal server error (transactional or other)",
)
g.add_option(
    "-p",
    action="store_true",
    dest="statusPartial",
    default=False,
    help="partial transaction",
)
p.add_option_group(g)
options, files = p.parse_args()
if options.userAttrs is None:
    options.userAttrs = [1, 2, 3, 4]
else:
    if 0 in options.userAttrs:
        if any(a != 0 for a in options.userAttrs):
            p.error("incompatible user print options")
        options.userAttrs = []
if options.users is None:
    options.users = []
if options.groups is None:
    options.groups = []
if len(files) == 0:
    files = [None]


def error(file, lineNo, message):
    sys.stderr.write("%s, line %d: %s\n" % (file, lineNo, message))


class Record(object):
    def __init__(self, file, lineNo, timestamp, beginRecord, tid=None):
        self.file = file
        self.lineNo = lineNo
        self.timestamp = timestamp
        self.beginRecord = beginRecord
        self.progressRecords = []
        self.endRecord = None
        self.tid = tid
        self.elapsed = 0.0


def recordHasUser(beginRecord):
    return beginRecord[0] != "otherError"


def userFilter(beginRecord):
    if len(options.users) == 0 and len(options.groups) == 0:
        return True
    if recordHasUser(beginRecord) and (
        beginRecord[2] in options.users or beginRecord[4] in options.groups
    ):
        return True
    return False


def typeFilter(beginRecord):
    if not options.typeReal and not options.typeTest:
        return True
    if beginRecord[0] == "otherError" or beginRecord[0].startswith("search/"):
        return False
    if util2.isTestIdentifier(beginRecord[1]) and options.typeTest:
        return True
    if not util2.isTestIdentifier(beginRecord[1]) and options.typeReal:
        return True
    return False


def operationFilter(beginRecord):
    if (
        not options.operationMint
        and not options.operationCreate
        and not options.operationGet
        and not options.operationSet
        and not options.operationDelete
        and not options.operationSearch
    ):
        return True
    if beginRecord[0] == "mintIdentifier" and options.operationMint:
        return True
    if beginRecord[0] == "createIdentifier" and options.operationCreate:
        return True
    if beginRecord[0] == "getMetadata" and options.operationGet:
        return True
    if beginRecord[0] == "setMetadata" and options.operationSet:
        return True
    if beginRecord[0] == "deleteIdentifier" and options.operationDelete:
        return True
    if beginRecord[0].startswith("search/") and options.operationSearch:
        return True
    return False


def statusFilter(endRecord):
    if (
        not options.statusSuccess
        and not options.statusBadRequest
        and not options.statusError
        and not options.statusPartial
    ):
        return True
    if endRecord[0] == "SUCCESS" and options.statusSuccess:
        return True
    if endRecord[0] in ["BADREQUEST", "FORBIDDEN"] and options.statusBadRequest:
        return True
    if endRecord[0] == "ERROR" and options.statusError:
        return True
    if endRecord[0] == "(incomplete)" and options.statusPartial:
        return True
    return False


def passesFilters(record):
    if options.from_ is not None and record.timestamp < options.from_:
        return False
    if options.to is not None and record.timestamp >= options.to:
        return False
    if not userFilter(record.beginRecord):
        return False
    if not typeFilter(record.beginRecord):
        return False
    if not operationFilter(record.beginRecord):
        return False
    if not statusFilter(record.endRecord):
        return False
    return True


def parseTimestamp(timestamp):
    t = calendar.timegm(time.strptime(timestamp[:19], "%Y-%m-%d %H:%M:%S"))
    return t + int(timestamp[20:]) / 1000.0


pattern = re.compile(
    "(\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2},\\d{3}) "
    + "(([\\da-fA-F]{32}) (BEGIN|PROGRESS|END) |- (STATUS|ERROR) )(.*)"
)

# Below, 'records' holds Record objects which are complete (i.e.,
# their END records have been encountered) and which pass the display
# filters.  'tidMap' maps transaction IDs to Record objects, both
# those in 'records' and those for which END records have not yet been
# encountered.  When an END record is encountered and the Record
# object is completed, if the transaction is not selected for display,
# the transaction's ID is retained in 'tidMap' but the Record object
# is discarded to save memory.  (Memory consumption has been a problem
# running this script on large log files.)

records = []
tidMap = {}

for file in files:
    if file is not None:
        f = open(file)
    else:
        f = sys.stdin
    n = 0
    for l in f:
        n += 1
        m = pattern.match(l)
        if not m:
            error(file, n, "unrecognized record")
            continue
        if m.group(2).startswith("-"):
            if m.group(5) == "STATUS":
                # Ignore status records.
                pass
            else:
                r = Record(file, n, m.group(1), ["otherError"])
                r.endRecord = ["ERROR"] + m.group(6).split(" ")
                if passesFilters(r):
                    records.append(r)
        else:
            tid = m.group(3)
            if m.group(4) == "BEGIN":
                if tid in tidMap:
                    error(file, n, "duplicate transaction ID")
                    continue
                r = Record(file, n, m.group(1), m.group(6).split(" "), tid)
                tidMap[tid] = r
            elif m.group(4) == "PROGRESS":
                if tid not in tidMap:
                    error(file, n, "no corresponding BEGIN record")
                    continue
                tidMap[tid].progressRecords.append(m.group(6))
            else:
                if tid not in tidMap:
                    error(file, n, "no corresponding BEGIN record")
                    continue
                r = tidMap[tid]
                if r.endRecord is not None:
                    error(file, n, "duplicate END record")
                    continue
                startTime = parseTimestamp(r.timestamp)
                endTime = parseTimestamp(m.group(1))
                if startTime > endTime:
                    error(file, n, "END record predates BEGIN record")
                    continue
                r.elapsed = endTime - startTime
                r.endRecord = m.group(6).split(" ")
                # Overwrite the timestamp with the transaction's ending
                # timestamp, so that transactions are ordered by completion
                # time, not start time.
                r.timestamp = m.group(1)
                if passesFilters(r):
                    records.append(r)
                else:
                    tidMap[tid] = None
    f.close()

for r in list(tidMap.values()):
    if type(r) is Record:
        if r.endRecord is None:
            if options.statusPartial:
                r.endRecord = ["(incomplete)", "tid=" + r.tid]
                if passesFilters(r):
                    records.append(r)
            else:
                error(r.file, r.lineNo, "no corresponding END record")

records.sort(key=lambda r: r.timestamp)

for r in records:
    if recordHasUser(r.beginRecord):
        br = r.beginRecord[:2]
        for i in range(1, 5):
            if i in options.userAttrs:
                br.append(r.beginRecord[i + 1])
        r.beginRecord = br + r.beginRecord[6:]
    if options.printTids:
        if r.tid is not None:
            tid = " " + r.tid
        else:
            tid = " -"
    else:
        tid = ""
    if options.printElapsedTimes:
        elapsed = " %.3f" % r.elapsed
    else:
        elapsed = ""
    print(
        f"{r.timestamp}{tid}{elapsed} {' '.join(r.beginRecord)} -> {' '.join(r.endRecord)}"
    )
    if options.printProgressRecords:
        for pr in r.progressRecords:
            print("\t" + pr)
