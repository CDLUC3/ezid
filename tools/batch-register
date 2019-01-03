#! /usr/bin/env python

# Batch registers identifiers.  Reads an input CSV file containing
# identifier metadata, one row per identifier; transforms the metadata
# into EZID metadata as directed by a configuration file of mappings;
# creates or mints identifiers, or updates existing identifiers; and
# outputs a CSV file containing the created, minted, or updated
# identifiers and other information.
#
# All input files are assumed to be UTF-8 encoded, and the output is
# UTF-8 encoded.
#
# Usage: batch-register [options] operation mappings input.csv
#
#   operation: create, mint, or update
#
#   mappings: configuration file, described below
#
#   input.csv: input metadata in CSV form
#
#   options:
#     -c CREDENTIALS  Either username:password, or just username
#                     (password will be prompted for), or
#                     sessionid=... (as obtained by using the EZID
#                     client tool).
#     -o COLUMNS      Comma-separated list of columns to output.
#                     Defaults to _n,_id,_error.
#     -p              Preview mode.  Don't register identifiers;
#                     instead, write transformed metadata to standard
#                     output.
#     -r              Remove any mapping to _id; useful when
#                     temporarily minting.
#     -s SHOULDER     The shoulder to mint under, e.g.,
#                     ark:/99999/fk4.
#     -t              Tab mode.  The input metadata is tab-separated
#                     (multiline values and tab characters in values
#                     are not supported).
#
# The mappings file defines how input CSV columns are mapped to EZID
# metadata elements.  Each line of the file should have the form:
#
#   destination = expression
#
# The destination in a mapping may be either an EZID element name
# (erc.who, dc.title, _target, etc.) or an XPath absolute path of a
# DataCite metadata schema element or attribute (e.g.,
# /resource/titles/title for an element,
# /resource/titles/title@titleType for an attribute).  If any XPaths
# are present, a DataCite XML record is constructed and assigned as
# the value of EZID element 'datacite'.  A special destination
# element, _id, should be used to identify the identifier to create or
# update when performing either of those operations.
#
# The expression in a mapping is a string in which zero or more column
# values may be interpolated.  Columns are referenced using 1-based
# indexing and may be referred to using the syntaxes "$n" or "${n}".
# Use "$$" for a literal dollar sign.
#
# For example, given an input CSV file with six columns
#
#   title,author,orcid,publisher_name,publisher_place,url
#
# a complete mapping to mint DOI identifiers would be:
#
#   _profile = datacite
#   /resource/titles/title = $1
#   /resource/creators/creator/creatorName = $2
#   /resource/creators/creator/nameIdentifier = $3
#   /resource/creators/creator/nameIdentifier@nameIdentifierScheme = ORCID
#   /resource/publisher = $4 ($5)
#   /resource/publicationYear = 2018
#   /resource/resourceType@resourceTypeGeneral = Dataset
#   _target = $6
#
# For another example, to update the statuses of a batch of existing
# identifiers to public, given an input file listing the identifiers
# (i.e., a CSV file with just one column), a mapping file would be:
#
#   _id = $1
#   _status = public
#
# A column may also be referenced as "${n:f}"; in this case the column
# value will first be passed to a function "f" and the return value of
# the function will be interpolated.  The referenced function should
# be defined in a module "functions", which should be supplied by the
# user of this script (the PYTHONPATH environment variable may need to
# be set for the module to be found).  Multiple column values can be
# passed to a function using the syntax "${n1,n2,n3,...:f}".
#
# For an example of using a user-supplied function, suppose that the
# CSV file in the first example above has a seventh column,
# publication_date, containing an ISO 8601 date.  Then a mapping for
# the publication year would be
#
#   /resource/publicationYear = ${7:year_only}
#
# with, in functions.py:
#
#   def year_only(v):
#     return v[:4]
#
# Limitations: It is not possible to update just a portion of existing
# DataCite XML records.  The order of mappings determines the ordering
# of XML elements.  When mapping to both a DataCite metadata schema
# element and attribute of that element, the mapping to the element
# must come first in the mappings file.
#
# Multiple mappings to EZID metadata elements and to DataCite metadata
# schema attributes are not supported; the last mapping overwrites any
# previous mappings.  But for DataCite metadata schema elements,
# multiple mappings cause multiple XML elements to be created.
# Specifically, given an XPath /resource/path/terminus, a new terminus
# element is created for each mapping.  Continuing with our running
# example, given eighth and ninth CSV columns
#
#   ...,subject1,subject2
#
# and additional mappings
#
#   /resource/subjects/subject = $8
#   /resource/subjects/subject = $9
#
# then the following XML structure would be created:
#
#   <resource>
#     ...
#     <subjects>
#       <subject>$8</subject>
#       <subject>$9</subject>
#     </subjects>
#   </resource>
#
# User-supplied functions provide considerably more flexibility in
# mapping, and are required in certain cases to create the necessary
# hierarchical DataCite XML structure.  A user-supplied function may
# return:
#
#   1. A string value, as illustrated previously.
#
#   2. A tuple (relpath, value) where relpath is an XPath relative
#      path of a DataCite metadata schema element or attribute, and
#      value is any valid return from a user-supplied function (i.e.,
#      a string, tuple, or list).  The path is interpreted relative to
#      the terminus element in the mapping or, in nested cases, to the
#      previous contextual node; and the path establishes a new
#      contextual node against which the value is processed.
#
#   3. A list of zero or more tuples.
#
# For example, suppose our CSV file has a tenth column containing zero
# or more editor names separated by semicolons.  A mapping
#
#   /resource/contributors = ${10:split_editors}
#
# and a function
#
#   def split_editors(v):
#     if v == "":
#       return ""
#     else:
#       return [( "contributor",
#                 [("contributorName", n), (".@contributorType", "Editor")] )\
#               for n in v.split(";")]
#
# would create the XML structure DataCite requires, namely:
#
#   <resource>
#     <contributors>
#       <contributor contributorType="Editor">
#         <contributorName>first editor</contributorName>
#       </contributor>
#       <contributor contributorType="Editor">
#         <contributorName>second editor</contributorName>
#       </contributor>
#       ...
#     </contributors>
#   </resource>
#
# The output, written to standard output, is a CSV file whose columns
# can be configured using the -o option.  An output column may be any
# metadata element populated by the above mapping process (referenced by
# element name) or any input column (referenced by simple integer).
# Three additional columns may be specified: _n, the record number in
# the input file; _id, the identifier created, minted, or updated; and
# _error, the error message in case of registration failure.
# Continuing the first example, to return three columns, identifier,
# title, and url, specify
#
#   -o _id,1,6
#
# The default output is _n,_id,_error.
#
# The -p ("preview mode") option can be used to examine the metadata
# that will be submitted, allowing confirmation that the
# transformation is operating as expected.  Before running a batch
# create or mint job it may also be helpful to first mint using a test
# shoulder to ensure that all metadata is well-formed and accepted.
# The test shoulders are ark:/99999/fk4 for ARK identifiers and
# doi:10.5072/FK2 for DOI identifiers.
#
# Greg Janee <gjanee@ucop.edu>
# November 2018

import argparse
import base64
import csv
import getpass
import re
import sys
import urllib
import urllib2
# We'd prefer to use LXML, but stick with the inferior built-in
# library for better portability.
import xml.etree.ElementTree

def loadMappings (file):
  # returns: [(destination, expression), ...]
  m = []
  with open(file) as f:
    n = 0
    for l in f:
      n += 1
      try:
        l = l.decode("UTF-8")
        assert "=" in l, "invalid syntax"
        d, e = [v.strip() for v in l.split("=", 1)]
        if d.startswith("/"):
          assert re.match("/resource(/\w+)+(@\w+)?$", d),\
            "invalid absolute XPath expression"
        else:
          assert re.match("[.\w]+$", d), "invalid element name"
        m.append((d, e))
      except Exception, e:
        assert False, "%s, line %d: %s" % (file, n, str(e))
  return m

def parseOutputColumns (columns, mappings):
  # columns: "element,1,2,..."
  # mappings: [(destination, expression), ...]
  # returns: ["element", 0, 1, ...]
  elements = [d for d, e in mappings if not d.startswith("/")] +\
    ["_n", "_id", "_error"]
  l = []
  for c in columns.split(","):
    try:
      i = int(c)
      # We'll check the upper bound on the column reference after
      # reading the first input row.
      assert i > 0, "argument -o: invalid input column reference"
      l.append(i-1)
    except ValueError:
      assert c in elements, "argument -o: no such output element: " + c
      l.append(c)
  return l

def interpolate (expression, row):
  # expression: string in which $n, ${n}, ${n:f}, $$ will be interpolated
  # row: [value1, value2, ...]
  # returns: string or complex object
  v = ""
  i = 0
  for m in re.finditer("\$(?:\d+|{\d+}|{\d+(?:,\d+)*:\w+}|\$)", expression):
    v += expression[i:m.start()]
    try:
      if m.group(0) == "$$":
        v += "$"
      elif m.group(0).startswith("${"):
        if ":" in m.group(0):
          cols, f = m.group(0)[2:-1].split(":")
          args = [row[int(c)-1] for c in cols.split(",")]
          try:
            import functions
            r = getattr(functions, f)(*args)
            if isinstance(r, basestring):
              v += r
            else:
              # We allow a function to return a complex object only if
              # the expression consists of the function reference and
              # nothing more--- and in this case, the object can be
              # returned immediately.
              assert m.group(0) == expression, "unsupported interpolation: " +\
                "function returned complex object but there is " +\
                "other text in expression"
              return r
          except Exception, e:
            assert False, "error calling user-supplied function %s: %s" %\
              (f, str(e))
        else:
          v += row[int(m.group(0)[2:-1])-1]
      else:
        v += row[int(m.group(0)[1:])-1]
    except IndexError:
      assert False, "input column reference exceeds number of columns"
    i = m.end()
  v += expression[i:]
  return v.strip()

def setDataciteValue (node, path, value):
  # node: XML node or None
  # path: "/resource/abspath@attribute" or "relpath@attribute"
  # value: string or complex object
  # returns: node if node was supplied, else root node
  def q (tag):
    return "{http://datacite.org/schema/kernel-4}" + tag
  if type(value) is tuple: value = [value]
  if type(value) is list:
    if len(value) == 0: return node
    assert all(type(v) is tuple and len(v) == 2 and\
      isinstance(v[0], basestring) for v in value),\
      "invalid return value from user-supplied function: " +\
      "malformed list or tuple"
    assert all(re.match("(\w+|[.])(/(\w+|[.]))*(@\w+)?$", v[0])\
      for v in value),\
      "invalid return value from user-supplied function: " +\
      "invalid relative XPath expression"
  elif isinstance(value, basestring):
    value = value.strip()
    if value == "": return node
  else:
    assert False, "invalid return value from user-supplied function"
  p = path[10 if path.startswith("/resource/") else 0:].split("/")
  a = None
  if "@" in p[-1]: p[-1], a = p[-1].split("@")
  if node == None:
    node = xml.etree.ElementTree.Element(q("resource"))
    node.attrib[
      "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"] =\
      "http://datacite.org/schema/kernel-4 " +\
      "http://schema.datacite.org/meta/kernel-4/metadata.xsd"
    n = xml.etree.ElementTree.SubElement(node, q("identifier"))
    n.attrib["identifierType"] = "(:tba)"
    n.text = "(:tba)"
  n = node
  for i, e in enumerate(p):
    if e != ".":
      # If we're at the terminal element of the path and we're not
      # setting an attribute, we always add a new child element.
      if i == len(p)-1 and a == None:
        c = None
      else:
        c = n.find(q(e))
      if c != None:
        n = c
      else:
        n = xml.etree.ElementTree.SubElement(n, q(e))
  if a != None:
    assert isinstance(value, basestring),\
      "unsupported interpolation: attribute %s requires string value" % a
    n.attrib[a] = value
  else:
    if isinstance(value, basestring):
      n.text = value
    else:
      for relpath, v in value: setDataciteValue(n, relpath, v)
  return node

def transform (args, mappings, row):
  # mappings: [(destination, expression), ...]
  # row: [value1, value2, ...]
  # returns: metadata dictionary
  md = {}
  dr = None
  for i, (d, e) in enumerate(mappings):
    try:
      v = interpolate(e, row)
      if d.startswith("/"):
        dr = setDataciteValue(dr, d, v)
      else:
        assert isinstance(v, basestring), "unsupported interpolation: " +\
          "user-supplied function must return string value in mapping to " +\
          "EZID metadata element"
        md[d] = v
    except AssertionError, err:
      assert False, "%s, line %d: %s" % (args.mappingsFile, i+1, str(err))
  if dr != None:
    if args.operation == "mint":
      s = args.shoulder
    else:
      s = md["_id"]
    dr.findall("*[@identifierType]")[0].attrib["identifierType"] =\
      "ARK" if s.startswith("ark:/") else "DOI"
    md["datacite"] = xml.etree.ElementTree.tostring(dr)
  return md

def toAnvl (record):
  # record: metadata dictionary
  # returns: string
  def escape (s, colonToo=False):
    if colonToo:
      p = "[%:\r\n]"
    else:
      p = "[%\r\n]"
    return re.sub(p, lambda c: "%%%02X" % ord(c.group(0)), s)
  return "".join("%s: %s\n" % (escape(k, True), escape(record[k])) for k in\
    sorted(record.keys()))

def process1 (args, record):
  # record: metadata dictionary
  # returns: (identifier or None, "error: ..." or None)
  # N.B.: _id is removed from record
  if args.operation == "mint":
    id = None
    if args.removeIdMapping and "_id" in record: del record["_id"]
    r = urllib2.Request("https://ezid.cdlib.org/shoulder/" +
      urllib.quote(args.shoulder, ":/"))
  else:
    id = str(record["_id"])
    del record["_id"]
    r = urllib2.Request("https://ezid.cdlib.org/id/" + urllib.quote(id, ":/"))
    r.get_method = lambda: "PUT" if args.operation == "create" else "POST"
  s = toAnvl(record).encode("UTF-8")
  r.add_data(s)
  r.add_header("Content-Type", "text/plain; charset=UTF-8")
  r.add_header("Content-Length", str(len(s)))
  if args.cookie != None:
    r.add_header("Cookie", args.cookie)
  else:
    r.add_header("Authorization",
      "Basic " + base64.b64encode(args.username + ":" + args.password))
  c = None
  try:
    c = urllib2.urlopen(r)
    s = c.read().decode("UTF-8")
    assert s.startswith("success:"), s
    return (s[8:].split()[0], None)
  except urllib2.HTTPError, e:
    if e.fp != None:
      s = e.fp.read().decode("UTF-8")
      if not s.startswith("error:"): s = "error: " + s
      return (id, s)
    else:
      return (id, "error: %d %s" % (e.code, e.msg))
  except Exception, e:
    return (id, "error: " + str(e))
  finally:
    if c != None: c.close()

def formOutputRow (args, row, record, recordNum, id, error):
  # row: [value1, value2, ...]
  # record: metadata dictionary
  # id: identifier or None
  # error: error message or None
  # returns: list
  l = []
  for c in args.outputColumns:
    if type(c) is int:
      l.append(row[c])
    else:
      if c == "_n":
        l.append(str(recordNum))
      elif c == "_id":
        l.append(id or "")
      elif c == "_error":
        l.append(error or "")
      else:
        l.append(record[c])
  return l

def process (args, mappings):
  class StrictTabDialect (csv.Dialect):
    delimiter = "\t"
    quoting = csv.QUOTE_NONE
    doublequote = False
    lineterminator = "\r\n"
  w = csv.writer(sys.stdout)
  n = 0
  for row in csv.reader(open(args.inputFile),
    dialect=(StrictTabDialect if args.tabMode else csv.excel)):
    n += 1
    if n == 1:
      numColumns = len(row)
      assert max([-1] + [c for c in args.outputColumns if type(c) is int]) <\
        numColumns,\
        "argument -o: input column reference exceeds number of columns"
    try:
      assert len(row) == numColumns, "inconsistent number of columns"
      row = [c.decode("UTF-8") for c in row]
      record = transform(args, mappings, row)
      if args.previewMode:
        sys.stdout.write("\n")
        sys.stdout.write(toAnvl(record).encode("UTF-8"))
      else:
        id, error = process1(args, record)
        w.writerow([c.encode("UTF-8")\
          for c in formOutputRow(args, row, record, n, id, error)])
        sys.stdout.flush()
    except Exception, e:
      assert False, "record %d: %s" % (n, str(e))

def main ():
  def validateShoulder (s):
    if not (s.startswith("ark:/") or s.startswith("doi:")):
      raise argparse.ArgumentTypeError("invalid shoulder")
    return s
  p = argparse.ArgumentParser(description="Batch registers identifiers.")
  p.add_argument("operation", choices=["create", "mint", "update"],
    help="operation to perform")
  p.add_argument("mappingsFile", metavar="mappings", help="configuration file")
  p.add_argument("inputFile", metavar="input.csv",
    help="input metadata in CSV form")
  p.add_argument("-c", metavar="CREDENTIALS", dest="credentials",
    help="either username:password, or just username (password will be " +\
    "prompted for), or session=... (as obtained by using the " +\
    "EZID client tool)")
  p.add_argument("-o", metavar="COLUMNS", dest="outputColumns",
    default="_n,_id,_error",
    help="comma-separated list of columns to output, defaults to " +\
      "_n,_id,_error")
  p.add_argument("-p", dest="previewMode", action="store_true",
    help="preview mode: don't register identifiers, instead, write " +\
    "transformed metadata to standard output")
  p.add_argument("-r", dest="removeIdMapping", action="store_true",
    help="remove any mapping to _id; useful when temporarily minting")
  p.add_argument("-s", metavar="SHOULDER", dest="shoulder",
    type=validateShoulder,
    help="the shoulder to mint under, e.g., ark:/99999/fk4")
  p.add_argument("-t", dest="tabMode", action="store_true",
    help="tab mode: the input metadata is tab-separated (multiline values " +\
      "and tab characters in values are not supported)")
  args = p.parse_args(sys.argv[1:])
  if not args.previewMode:
    assert args.credentials != None, "operation requires -c argument"
  if args.operation == "mint":
    assert args.shoulder != None, "operation requires -s argument"
  mappings = loadMappings(args.mappingsFile)
  if args.operation in ["create", "update"]:
    assert "_id" in [d for d, e in mappings],\
      "operation requires mapping to _id"
  args.outputColumns = parseOutputColumns(args.outputColumns, mappings)
  if not args.previewMode:
    if args.credentials.startswith("sessionid="):
      args.cookie = args.credentials
    else:
      args.cookie = None
      if ":" in args.credentials:
        args.username, args.password = args.credentials.split(":", 1)
      else:
        args.username = args.credentials
        args.password = getpass.getpass()
  process(args, mappings)

try:
  main()
except Exception, e:
  sys.stderr.write("%s: error: %s\n" % (sys.argv[0].split("/")[-1], str(e)))
  sys.exit(1)
