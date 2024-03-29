#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""The 'dump-store', 'dump-binder', 'select', and 'project' scripts
form a dump file query system.

The general usage is:

   dump-* | select constraint... | project fields...

This script reads a dump file (normal or raw) from standard input, applies a constraint
expression to each record, and writes the successful records to standard output. The
input may be gzip-compressed, but the output is never compressed.

Usage: select [options] constraint...

Options:
  -m IDMAP      convert agent identifiers to local names using IDMAP
  -z            gunzip the input

The -m option is useful when reading records in which agent identifiers have *not* been
converted; the specified IDMAP mapping file must be one produced by the 'idmap' script.
(Agent identifiers are converted only for the purpose of constraint evaluation; they are
unchanged on output.)

The constraint expression is specified directly on the command line. A basic constraint
has the form

   field operator value

e.g.,
   _owner = gjanee

An identifier record satisfies a basic constraint if the record has a non-empty value
for the field and if the record value has the relationship to the constraint value as
indicated by the operator. The relational operators (<, <=, =, >=, >) and regular
expression match operator (=~) are supported. In the latter case, the constraint value
must be a regular expression expressed using the Perl-like syntax /regexp/ or
/regexp/flags. A forward slash (/) can be placed in the regular expression by preceding
it with a backward slash (\). The i, m, and s flags have their usual interpretations.

For example:

   _id =~ /doi:10\.5072\/FK2/i

There's no fancy parser here, so operators and other syntactic tokens must appear as
separate command line arguments. Furthermore, operators such as < must be quoted to
avoid interpretation by the shell. To prevent interpretation of a field or value as a
reserved word or punctuation or operator, quote it. But quotes themselves must be quoted
to avoid interpretation by the shell, so, sadly, quotes will resemble:

   datacite.title = "'and'"

A basic constraint can be negated by placing "not" before it, and constraints can be
combined using "and" and "or". Boolean expressions can be grouped using both
parentheses and curly braces (curly braces don't require shell quoting). Example of a
boolean expression:

   _owner = gjanee or { _ownergroup = cdl and not _owner = jak }

There are some special fields. The _id field holds the identifier. The _fields field is
an array of all metadata fields present in the identifier record and can be used in
conjunction with the "contains" operator, as in:

   _fields contains erc.what

The timestamp fields _created and _updated can be compared against dates or times
specified in ISO YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS syntaxes. Times are interpreted
relative to the local timezone. If only a date is specified in the constraint,
comparisons are performed on dates only.

The _numFields field is a slight syntactic exception in that it must be followed by a
regular expression; it is the number of non-internal fields in the record whose names
match the regular expression. For example, to select identifiers having at least one
field beginning with "erc.":

   _numFields /erc\./ > 0

Finally, there are a number of pre-defined macros:

   _ark                  Is an ARK identifier.
   _doi                  Is a DOI identifier.
   _uuid                 Is a UUID identifier.

   _real                 Is a real (i.e., non-test) identifier.
   _test                 Is a test identifier.

   _public               Is public.
   _reserved             Is reserved.
   _unavailable          Is unavailable.

   _exported             Is exported.

   _anyMetadata          Has any citation (non-internal) metadata.
   _anyDatacite          Has any Datacite metadata.
   _anyDublinCore        Has any Dublin Core metadata.
   _anyErc               Has any ERC metadata.

   _completeErc          Has complete (who/what/when or blob) ERC metadata.
   _minimumDatacite      Has (via mapping) minimum Datacite metadata.

   _numDataciteFields    Number of Datacite fields.
   _numDublinCoreFields  Number of Dublin Core fields.
   _numErcFields         Number of ERC fields.

Example of macro use:

   _owner = gjanee and _ark and _real and not _exported

This script requires an EZID module. The PYTHONPATH environment variable must include
the .../SITE_ROOT/PROJECT_ROOT/impl directory; if it doesn't, we attempt to dynamically
locate it and add it.
"""

import gzip
import optparse
import re
import sys
import time

# Globals set below...
# options = None
import impl.util

idmap = None


def isRelationalOperator(t):
    return t in ["<", "<=", "=", ">=", ">"]


def isOperator(t):
    return isRelationalOperator(t) or t in ["=~", "contains"]


class Constraint(object):
    def evaluate(self, record):
        pass


class FieldConstraint(Constraint):
    def __init__(self, field, operator, value):
        if type(field) is tuple:
            assert (
                field[0] == "_numFields"
                and type(field[1]).__name__ == "SRE_Pattern"
                and isRelationalOperator(operator)
                and type(value) is int
            )
        else:
            assert type(field) is str
            if field in ["_c", "_created", "_u", "_updated"]:
                assert (
                    isRelationalOperator(operator)
                    and type(value) is tuple
                    and len(value) == 2
                    and type(value[0]) is int
                    and type(value[1]) is str
                )
            elif field == "_fields":
                assert operator == "contains" and type(value) is str
            else:
                assert (isRelationalOperator(operator) and type(value) is str) or (
                    operator == "=~" and type(value).__name__ == "SRE_Pattern"
                )
        self.field = field
        self.operator = operator
        if field in ["_c", "_created", "_u", "_updated"]:
            self.value = value[0]
            self.precision = value[1]
        else:
            self.value = value

    def evaluate(self, record):
        if type(self.field) is tuple:
            v = 0
            for k in record:
                if not k.startswith("_") and self.field[1].match(k):
                    v += 1
        elif self.field in ["_c", "_created", "_u", "_updated"]:
            if self.field not in record:
                return False
            if self.precision == "YMDHMS":
                v = int(record[self.field])
            else:
                t = time.localtime(int(record[self.field]))
                v = int(
                    time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, 0, 1, -1))
                )
        elif self.field in ["_o", "_owner", "_g", "_ownergroup"] and options.idmap:
            if self.field not in record:
                return False
            v = idmap.get(record[self.field], record[self.field])
        elif self.field == "_fields":
            v = record
        else:
            if self.field not in record:
                return False
            v = record[self.field]
        if self.operator == "<":
            return v < self.value
        elif self.operator == "<=":
            return v <= self.value
        elif self.operator == "=":
            return v == self.value
        elif self.operator == ">=":
            return v >= self.value
        elif self.operator == ">":
            return v > self.value
        elif self.operator == "=~":
            return self.value.match(v) is not None
        elif self.operator == "contains":
            return self.value in v
        else:
            assert False


class BooleanConstraint(Constraint):
    def __init__(self, operator, constraints):
        assert operator in ["and", "or", "not"]
        assert (operator == "not" and len(constraints) == 1) or (
            operator != "not" and len(constraints) > 1
        )
        self.operator = operator
        self.constraints = constraints

    def evaluate(self, record):
        if self.operator == "not":
            return not self.constraints[0].evaluate(record)
        elif self.operator == "and":
            for c in self.constraints:
                if not c.evaluate(record):
                    return False
            return True
        else:
            for c in self.constraints:
                if c.evaluate(record):
                    return True
            return False


def replaceMacro(query):
    if query[0] == "_anyDatacite":
        e = "_numDataciteFields > 0"
    elif query[0] == "_anyDublinCore":
        e = "_numDublinCoreFields > 0"
    elif query[0] == "_anyErc":
        e = "_numErcFields > 0"
    elif query[0] == "_anyMetadata":
        e = "_numFields /.*/ > 0"
    elif query[0] == "_ark":
        e = "_id =~ /ark:\\//"
    elif query[0] == "_completeErc":
        e = (
            "( ( _fields contains erc and erc =~ /.*^who:/ms and "
            + "erc =~ /.*^what:/ms and erc =~ /.*^when:/ms ) or ( _fields "
            + "contains erc.who and _fields contains erc.what and _fields contains "
            + "erc.when ) )"
        )
    elif query[0] == "_doi":
        e = "_id =~ /doi:/"
    elif query[0] == "_exported":
        e = (
            "( _export = yes or ( not _fields contains _export and not _fields "
            + "contains _x ) )"
        )
    elif query[0] == "_minimumDatacite":
        e = (
            "( _fields contains datacite or ( ( _fields contains "
            + "datacite.creator or ( ( _p = erc or _profile = erc ) and ( _fields "
            + "contains erc.who or ( _fields contains erc and erc =~ /.*^who:/ms "
            + ") ) ) or ( ( _p = dc or _profile = dc ) and _fields contains "
            + "dc.creator ) ) and ( _fields contains datacite.title or ( ( _p = "
            + "erc or _profile = erc ) and ( _fields contains erc.what or ( "
            + "_fields contains erc and erc =~ /.*^what:/ms ) ) ) or ( ( _p = dc "
            + "or _profile = dc ) and _fields contains dc.title ) ) and ( _fields "
            + "contains datacite.publisher or ( ( _p = dc or _profile = dc ) and "
            + "_fields contains dc.publisher ) ) and ( _fields contains "
            + "datacite.publicationyear or ( ( _p = erc or _profile = erc ) and "
            + "( _fields contains erc.when or ( _fields contains erc and erc =~ "
            + "/.*^when:/ms ) ) ) or ( ( _p = dc or _profile = dc ) and _fields "
            + "contains dc.date ) ) ) )"
        )
    elif query[0] == "_numDataciteFields":
        e = "_numFields /datacite($|\\.)/"
    elif query[0] == "_numDublinCoreFields":
        e = "_numFields /dc\\./"
    elif query[0] == "_numErcFields":
        e = "_numFields /erc($|\\.)/"
    elif query[0] == "_public":
        e = (
            "( _status = public or ( not _fields contains _status and not "
            + "_fields contains _is ) )"
        )
    elif query[0] == "_real":
        e = "not _test"
    elif query[0] == "_reserved":
        e = "( _status = reserved or _is = reserved )"
    elif query[0] == "_test":
        e = "( _id =~ /ark:\\/99999\\/fk4/ or _id =~ /doi:10\\.5072\\/FK2/ )"
    elif query[0] == "_unavailable":
        e = "( _status =~ /unavailable/ or _is =~ /unavailable/ )"
    elif query[0] == "_uuid":
        e = "_id =~ /uuid:/"
    else:
        e = None
    if e:
        l = e.split()
        l.reverse()
        del query[0]
        for t in l:
            query.insert(0, t)
        return True
    else:
        return False


def isReserved(t):
    return t in ["and", "or", "not", "{", "}", "(", ")"] or isOperator(t)


def consumeExpression(consumed, query):
    assert len(query) > 0, "expecting expression"
    l = [consumeConstraint(consumed, query)]
    o = None
    while len(query) > 0 and query[0] in ["and", "or"]:
        assert o is None or query[0] == o, "mixed boolean operators in expression"
        o = query[0]
        consumed.append(query[0])
        del query[0]
        l.append(consumeConstraint(consumed, query))
    if len(l) > 1:
        return BooleanConstraint(o, l)
    else:
        return l[0]


def consumeConstraint(consumed, query):
    assert len(query) > 0, "expecting constraint"
    while replaceMacro(query):
        pass
    if query[0] == "(" or query[0] == "{":
        close = ")" if query[0] == "(" else "}"
        consumed.append(query[0])
        del query[0]
        e = consumeExpression(consumed, query)
        assert len(query) > 0 and query[0] == close, "expecting " + close
        consumed.append(query[0])
        del query[0]
        return e
    elif query[0] == "not":
        consumed.append(query[0])
        del query[0]
        return BooleanConstraint("not", [consumeConstraint(consumed, query)])
    else:
        l = consumeTerm(consumed, query)
        if l == "_numFields":
            r = consumeRegexp(consumed, query)
            l = (l, r)
            o = consumeOperator(consumed, query, isRelationalOperator, "relational")
            r = consumeInteger(consumed, query)
        else:
            if l in ["_c", "_created", "_u", "_updated"]:
                o = consumeOperator(consumed, query, isRelationalOperator, "relational")
                r = consumeTimestamp(consumed, query)
            elif l == "_fields":
                o = consumeOperator(
                    consumed, query, lambda o: o == "contains", "contains"
                )
                r = consumeTerm(consumed, query)
            else:
                o = consumeOperator(
                    consumed, query, lambda o: o != "contains", "relational or =~"
                )
                if o == "=~":
                    r = consumeRegexp(consumed, query)
                else:
                    r = consumeTerm(consumed, query)
        return FieldConstraint(l, o, r)


def consumeTerm(consumed, query):
    assert len(query) > 0 and not isReserved(query[0]), "expecting term"
    if query[0].startswith("'") or query[0].startswith('"'):
        assert len(query[0]) > 1 and query[0][-1] == query[0][0], "missing quote"
        t = query[0][1:-1]
    else:
        t = query[0]
    consumed.append(query[0])
    del query[0]
    return t


def consumeOperator(consumed, query, additionalPredicate, errorMessage):
    assert len(query) > 0 and isOperator(query[0]), "expecting operator"
    assert additionalPredicate(query[0]), "expecting %s operator" % errorMessage
    o = query[0]
    consumed.append(query[0])
    del query[0]
    return o


def consumeRegexp(consumed, query):
    assert len(query) > 0, "expecting regexp"
    m = re.match("/((?:[^\\\\/]|\\\\.)*)/([ims]*)$", query[0])
    assert m, "expecting regexp"
    flags = 0
    if "i" in m.group(2):
        flags |= re.I
    if "m" in m.group(2):
        flags |= re.M
    if "s" in m.group(2):
        flags |= re.S
    try:
        r = re.compile(m.group(1), flags)
    except Exception:
        assert False, "expecting regexp"
    consumed.append(query[0])
    del query[0]
    return r


def consumeInteger(consumed, query):
    assert len(query) > 0 and re.match("\\d+$", query[0]), "expecting integer"
    i = int(query[0])
    consumed.append(query[0])
    del query[0]
    return i


def consumeTimestamp(consumed, query):
    assert len(query) > 0, "expecting timestamp"
    try:
        t = (int(time.mktime(time.strptime(query[0], "%Y-%m-%dT%H:%M:%S"))), "YMDHMS")
    except ValueError:
        try:
            t = (int(time.mktime(time.strptime(query[0], "%Y-%m-%d"))), "YMD")
        except ValueError:
            assert False, "expecting timestamp"
    consumed.append(query[0])
    del query[0]
    return t


p = optparse.OptionParser(usage="%prog [options] constraint...")
p.add_option(
    "-m",
    action="store",
    type="string",
    dest="idmap",
    default=None,
    help="map agent identifiers to local names using IDMAP",
)
p.add_option(
    "-z",
    action="store_true",
    dest="gunzipInput",
    default=False,
    help="gunzip the input",
)
options, query = p.parse_args()

if options.idmap:
    f = open(options.idmap)
    idmap = {}
    for l in f:
        id, name, agentType = l.split()
        idmap[id] = name
    f.close()

consumed = []
try:
    constraint = consumeExpression(consumed, query)
    assert len(query) == 0, "extra terms follow complete query"
except AssertionError as e:
    if len(consumed) > 0:
        c = " " + " ".join(consumed)
    else:
        c = ""
    if len(query) > 0:
        q = " " + " ".join(query)
    else:
        q = ""
    sys.stderr.write(
        ("select: query parse error at '***': %s\n" + "QUERY:%s ***%s\n")
        % (str(e), c, q)
    )
    sys.exit(1)

if options.gunzipInput:
    infile = gzip.GzipFile(fileobj=sys.stdin, mode="r")
else:
    infile = sys.stdin

for l in infile:
    id, record = impl.util.fromExchange(l, True)
    record["_id"] = id
    if constraint.evaluate(record):
        print(l, end=' ')
