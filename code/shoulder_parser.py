# =============================================================================
#
# EZID :: shoulder_parser.py
#
# Parses a shoulder file.  This module has been split out from
# shoulder.py so that it can be imported by offline tools without
# importing the rest of EZID.
#
# A shoulder file lists different types of entries, each of which has
# the general multi-line form:
#
#    :: key
#    field: value
#    field: value
#    ...
#
# Empty lines and lines beginning with "#" are ignored.
#
# There are currently two types of entries, shoulders and datacenters.
# For a shoulder, the entry key is the shoulder itself, in qualified
# and normalized form, as in "ark:/12345/xyz" or "doi:10.1234/XYZ".
# The required fields for a shoulder are:
#
#    type
#       Must be "shoulder".
#
#    manager
#       The entity that manages the shoulder; typically "ezid".
#
#    name
#       The shoulder's name, e.g., "Brown University Library".
#
#    minter
#       The absolute URL of the associated minter, or empty if none.
#
#    datacenter
#       For DOI shoulders (only), the qualified name of the DataCite
#       datacenter to use, e.g., "CDL.BUL".  Note that each referenced
#       datacenter must be defined by a datacenter entry (see below).
#
# The optional fields for a shoulder are:
#
#    active
#       Must be "true" or "false"; defaults to "true".  If "false",
#       the shoulder is not in active use, meaning that it is ignored
#       by EZID and that it does not participate in global validation
#       checks.
#
#    date
#       The date the shoulder was created in the syntax YYYY.MM.DD.
#
#    is_supershoulder
#    is_subshoulder
#       Must be "true" or "false"; if "true", indicates the shoulder
#       is a supershoulder (i.e., a prefix of) or a subshoulder (i.e.,
#       an extension of) another shoulder.  Useful for silencing
#       warnings related to subshoulders.
#
#    crossref
#       Must be "true" or "false"; if "true", indicates the shoulder
#       supports CrossRef registration.  May be used with DOI
#       shoulders only.
#
#    prefix_shares_datacenter
#       Must be "true" or "false"; if "true", the shoulder's
#       datacenter may be shared with another shoulder having a
#       different DOI prefix.  Useful for silencing warnings.  May be
#       used with DOI shoulders only.
#
# For a datacenter, the entry key is the datacenter symbol, prefixed
# with "datacite:" and uppercased, as in "datacite:CDL.BUL".  The
# required fields for a datacenter are:
#
#    type
#       Must be "datacenter".
#
#    manager
#       The entity that manages the datacenter; typically "ezid".
#
#    name
#       The datacenter's name, e.g., "Brown University Library".
#
# The optional fields for a datacenter are:
#
#    active
#       Must be "true" or "false"; defaults to "true".  If "false",
#       the datacenter is not in active use, meaning that it is
#       ignored by EZID and that it does not participate in global
#       validation checks.
#
#    date
#      The date the datacenter was created in the syntax YYYY.MM.DD.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2013, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import re

import util

_fields = {
  # entryType: { fieldName: isRequired, ... }
  "shoulder": {
    "manager": True,
    "name": True,
    "minter": True,
    "datacenter": False,
    "active": False,
    "date": False,
    "is_supershoulder": False,
    "is_subshoulder": False,
    "crossref": False,
    "prefix_shares_datacenter": False },
  "datacenter": {
    "manager": True,
    "name": True,
    "active": False,
    "date": False }
}

_shoulderManagers = ["ezid", "oca", "other"]

class Entry (dict):
  """
  A shoulder file entry.  This is a dictionary that maps field names
  to values (the entry key is stored under field name "key"), but for
  convenience fields can also be accessed as attributes.
  Additionally, for field F, Entry.lineNum.F is the line number at
  which F was defined (internal to this module only; lineNum
  attributes are removed by the parser when returned).
  """
  def __init__ (self, _createLineNum=True):
    if _createLineNum: self.lineNum = Entry(False)
  def __getattr__ (self, name):
    return self[name]
  def add (self, field, value, lineNum):
    """
    Adds a field to the entry.
    """
    self[field] = value
    self.lineNum[field] = lineNum

def _test (condition, message, lineNum, errors):
  if not condition: errors.append((lineNum, message))
  return condition

def _testAbort (condition, message, lineNum, errors):
  if not _test(condition, message, lineNum, errors): assert False

def _validateShoulder (entry, errors, warnings):
  returnValue = [True]
  def mytest (condition, message, lineNum):
    if not _test(condition, message, lineNum, errors): returnValue[0] = False
    return condition
  # Strategy for validating shoulders: a shoulder is valid if adding a
  # single character yields a valid identifier.
  if entry.key.startswith("ark:/"):
    v = util.validateArk(entry.key[5:] + "x")
    if mytest(v != None, "invalid ARK shoulder", entry.lineNum.key):
      mytest(v == entry.key[5:]+"x",
        "ARK shoulder is not in normalized form", entry.lineNum.key)
  elif entry.key.startswith("doi:"):
    v = util.validateDoi(entry.key[4:] + "X")
    if mytest(v != None, "invalid DOI shoulder", entry.lineNum.key):
      mytest(v == entry.key[4:]+"X",
        "DOI shoulder is not in normalized form", entry.lineNum.key)
  elif entry.key == "urn:uuid:":
    pass
  else:
    mytest(False, "invalid shoulder scheme", entry.lineNum.key)
  mytest(entry.manager in _shoulderManagers, "invalid shoulder manager",
    entry.lineNum.manager)
  mytest(entry.name != "", "empty shoulder name", entry.lineNum.name)
  if "date" in entry:
    mytest(re.match("\d{4}\.\d{2}\.\d{2}$", entry.date), "invalid date",
      entry.lineNum.date)
  mytest(entry.minter == "" or re.match("https?://", entry.minter),
    "invalid minter", entry.lineNum.minter)
  if "active" in entry:
    if mytest(entry.active in ["true", "false"],
      "invalid boolean value", entry.lineNum.active):
      entry["active"] = (entry.active == "true")
  else:
    entry["active"] = True
  if entry.key.startswith("doi:"):
    if mytest("datacenter" in entry, "missing DOI shoulder datacenter",
      entry.lineNum.key):
      mytest(
        re.match("[A-Z][-A-Z0-9]{0,6}[A-Z0-9]\.[A-Z][-A-Z0-9]{0,6}[A-Z0-9]$",
        entry.datacenter), "invalid datacenter syntax",
        entry.lineNum.datacenter)
    if "crossref" in entry:
      if mytest(entry.crossref in ["true", "false"],
        "invalid boolean value", entry.lineNum.crossref):
        entry["crossref"] = (entry.crossref == "true")
    else:
      entry["crossref"] = False
    if "prefix_shares_datacenter" in entry:
      if mytest(entry.prefix_shares_datacenter in ["true", "false"],
        "invalid boolean value", entry.lineNum.prefix_shares_datacenter):
        entry["prefix_shares_datacenter"] =\
          (entry.prefix_shares_datacenter == "true")
    else:
      entry["prefix_shares_datacenter"] = False
  else:
    if "datacenter" in entry:
      warnings.append((entry.lineNum.datacenter,
        "non-DOI shoulder has datacenter field"))
    if "crossref" in entry:
      warnings.append((entry.lineNum.crossref,
        "non-DOI shoulder has crossref field"))
    if "prefix_shares_datacenter" in entry:
      warnings.append((entry.lineNum.prefix_shares_datacenter,
        "non-DOI shoulder has prefix_shares_datacenter field"))
  for field in ["is_supershoulder", "is_subshoulder"]:
    if field in entry:
      if mytest(entry[field] in ["true", "false"], "invalid boolean value",
        entry.lineNum[field]):
        entry[field] = (entry[field] == "true")
  return returnValue[0]

def _validateDatacenter (entry, errors, warnings):
  returnValue = [True]
  def mytest (condition, message, lineNum):
    if not _test(condition, message, lineNum, errors): returnValue[0] = False
    return condition
  if mytest(entry.key.startswith("datacite:"),
    "missing 'datacite:' prefix", entry.lineNum.key):
    entry.key = entry.key[9:]
    mytest(
      re.match("[A-Z][-A-Z0-9]{0,6}[A-Z0-9]\.[A-Z][-A-Z0-9]{0,6}[A-Z0-9]$",
      entry.key), "invalid datacenter syntax", entry.lineNum.key)
  mytest(entry.manager in _shoulderManagers, "invalid datacenter manager",
    entry.lineNum.manager)
  mytest(entry.name != "", "empty datacenter name", entry.lineNum.name)
  if "active" in entry:
    if mytest(entry.active in ["true", "false"],
      "invalid boolean value", entry.lineNum.active):
      entry["active"] = (entry.active == "true")
  else:
    entry["active"] = True
  if "date" in entry:
    mytest(re.match("\d{4}\.\d{2}\.\d{2}$", entry.date), "invalid date",
      entry.lineNum.date)
  return returnValue[0]

def _validateEntry (entry, errors, warnings):
  try:
    _testAbort("type" in entry, "missing entry type", entry.lineNum.key,
      errors)
    _testAbort(entry.type in _fields, "invalid entry type", entry.lineNum.type,
      errors)
    missing = False
    for field, isRequired in _fields[entry.type].items():
      if not _test(not isRequired or field in entry,
        "missing %s %s" % (entry.type, field), entry.lineNum.key, errors):
        missing = True
    for field in entry:
      if field not in ["key", "type"] and field not in _fields[entry.type]:
        warnings.append((entry.lineNum[field], "unrecognized field"))
    if missing: return False
    if entry.type == "shoulder":
      return _validateShoulder(entry, errors, warnings)
    elif entry.type == "datacenter":
      return _validateDatacenter(entry, errors, warnings)
  except AssertionError:
    return False

def _read (fileContent, errors, warnings):
  entries = []
  entry = None
  lineNum = 0
  for line in fileContent.splitlines():
    lineNum += 1
    line = line.strip()
    if line.startswith("#") or line == "": continue
    try:
      if line.startswith("::"):
        if entry != None:
          if _validateEntry(entry, errors, warnings): entries.append(entry)
          entry = None
        key = line[2:].strip()
        _testAbort(key != "", "missing entry key", lineNum, errors)
        entry = Entry()
        entry.add("key", key, lineNum)
      else:
        _testAbort(entry != None, "no entry is being defined", lineNum, errors)
        _testAbort(":" in line, "syntax error: no colon in line", lineNum,
          errors)
        field, value = [v.strip() for v in line.split(":", 1)]
        _testAbort(field != "", "missing field name", lineNum, errors)
        _testAbort(field != "key", "reserved field name", lineNum, errors)
        _testAbort(field not in entry, "repeated field", lineNum, errors)
        entry.add(field, value, lineNum)
    except AssertionError:
      continue
  if entry != None and _validateEntry(entry, errors, warnings):
    entries.append(entry)
  return entries

def _globalValidations (entries, errors, warnings):
  shoulders = [e for e in entries if e.type == "shoulder" and e.active]
  # Test for duplicate shoulders and shoulder prefixes.
  shoulders.sort(key=lambda e: (e.key, e.lineNum.key))
  for i in range(len(shoulders)-1):
    _test(shoulders[i].key != shoulders[i+1].key, "duplicate shoulder",
      shoulders[i+1].lineNum.key, errors)
    if shoulders[i+1].key.startswith(shoulders[i].key) and\
      len(shoulders[i+1].key) > len(shoulders[i].key):
      if not shoulders[i].get("is_supershoulder", False) and\
        not shoulders[i+1].get("is_subshoulder", False):
        warnings.append((shoulders[i].lineNum.key,
          "shoulder is proper prefix of another shoulder"))
  # Test for duplicate shoulder names.
  def qualifiedName (shoulder):
    return shoulder.key.split(":", 1)[0] + shoulder.name
  shoulders.sort(key=lambda s: (qualifiedName(s), s.lineNum.name))
  for i in range(len(shoulders)-1):
    _test(qualifiedName(shoulders[i]) != qualifiedName(shoulders[i+1]),
      "duplicate shoulder name", shoulders[i+1].lineNum.name, errors)
  # Test for DOI prefixes shared across datacenters.
  shoulders.sort(key=lambda s: s.lineNum.key)
  d = {}
  for s in shoulders:
    if s.key.startswith("doi:") and "datacenter" in s:
      l = d.get(s.datacenter, [])
      l.append(s)
      d[s.datacenter] = l
  def getPrefix (s):
    return s.key.split("/", 1)[0]
  for dc, l in d.items():
    if len(l) > 1:
      p = getPrefix(l[0])
      if not all(getPrefix(s) == p for s in l[1:]):
        for s in l:
          if not s.prefix_shares_datacenter:
            warnings.append((s.lineNum.key,
              "datacenter is shared across DOI prefixes at lines " +\
              ", ".join("%d" % ss.lineNum.key for ss in l)))
  # Test for duplicate datacenters.
  datacenters = [e for e in entries if e.type == "datacenter" and e.active]
  datacenters.sort(key=lambda e: (e.key, e.lineNum.key))
  for i in range(len(datacenters)-1):
    _test(datacenters[i].key != datacenters[i+1].key, "duplicate datacenter",
      datacenters[i+1].lineNum.key, errors)
  # Test for duplicate datacenter names.
  datacenters.sort(key=lambda e: (e.name, e.lineNum.name))
  for i in range(len(datacenters)-1):
    _test(datacenters[i].name != datacenters[i+1].name,
      "duplicate datacenter name", datacenters[i+1].lineNum.name, errors)
  # Test for presence of datacenter definitions.
  datacenters = set(e.key for e in datacenters)
  for s in shoulders:
    if "datacenter" in s:
      _test(s.datacenter in datacenters, "undefined datacenter",
        s.lineNum.datacenter, errors)

def parse (fileContent):
  """
  Parses a shoulder file.  'fileContent' should be the file's entire
  contents as a single string.  Returns a 3-tuple (entries, errors,
  warnings) where 'entries' is a list of Entry objects and 'errors'
  and 'warnings' are each lists of tuples (line number, message).
  """
  errors = []
  warnings = []
  entries = _read(fileContent, errors, warnings)
  _globalValidations(entries, errors, warnings)
  for e in entries: del e.lineNum
  return (entries, errors, warnings)
