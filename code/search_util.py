# =============================================================================
#
# EZID :: search_util.py
#
# Search-related utilities.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.conf
import django.db
import django.db.models
import operator
import re
import time
import urlparse

import config
import ezidapp.models
import log
import util

_reconnectDelay = None
_fulltextSupported = None
_maxTargetLength = None

def _loadConfig ():
  global _reconnectDelay, _fulltextSupported, _maxTargetLength
  _reconnectDelay = int(config.get("databases.reconnect_delay"))
  _fulltextSupported =\
    django.conf.settings.DATABASES["search"]["fulltextSearchSupported"]
  _maxTargetLength = ezidapp.models.SearchIdentifier._meta.\
    get_field("searchableTarget").max_length

_loadConfig()
config.registerReloadListener(_loadConfig)

class AbortException (Exception):
  pass

def withAutoReconnect (functionName, function, continuationCheck=None):
  """
  Calls 'function' and returns the result.  If an operational database
  error is encountered (e.g., a lost connection), the call is repeated
  until it succeeds.  'continuationCheck', if not None, should be
  another function that signals when the attempts should cease by
  raising an exception or returning False.  If 'continuationCheck'
  returns False, this function raises AbortException (defined in this
  module).  'functionName' is the name of 'function' for logging
  purposes.
  """
  firstError = True
  while True:
    try:
      return function()
    except django.db.OperationalError, e:
      # We're silent about the first error because it might simply be
      # due to the database connection having timed out.
      if not firstError:
        log.otherError("search_util.withAutoReconnect/" + functionName, e)
        time.sleep(_reconnectDelay)
      if continuationCheck != None and not continuationCheck():
        raise AbortException()
      # In some cases a lost connection causes the thread's database
      # connection object to be permanently screwed up.  The following
      # call solves the problem.  (Note that Django's database
      # connection objects are indexed generically, but are stored
      # thread-local.)
      django.db.connections["search"].close()
      firstError = False

def ping ():
  """
  Tests the search database, returning "up" or "down".
  """
  try:
    n = ezidapp.models.SearchRealm.objects.count()
  except:
    return "down"
  else:
    return "up"

defaultSelectRelated = ["owner", "ownergroup"]
defaultDefer = ["cm", "keywords", "target", "searchableTarget",
  "resourceCreatorPrefix", "resourceTitlePrefix", "resourcePublisherPrefix"]

def formulateQuery (constraints, orderBy=None,
  selectRelated=defaultSelectRelated, defer=defaultDefer):
  """
  Formulates a search database query and returns an unevaluated
  QuerySet that can then be evaluated, indexed, etc.  'constraints'
  should be a dictionary mapping search columns to constraint values.
  The accepted search columns (most of which correspond to fields in
  the Identifier and SearchIdentifier models) and associated
  constraint Python types and descriptions are listed in the table
  below.  The 'R' flag indicates if multiple constraints may be placed
  against the column; if yes, multiple constraint values should be
  expressed as a list, and the constraints will be OR'd together.  The
  'O' flag indicates if the column may be used for ordering results.
  Descending ordering is achieved, Django-style, by prefixing the
  column name with a minus sign.

  =========================================================================
                      |   |   | constraint |
  search column       | R | O | type       | constraint value
  --------------------+---+---+------------+-------------------------------
  identifier          |   | Y | str        | qualified identifier, e.g.,
                      |   |   |            | "ark:/12345/foo", not
                      |   |   |            | necessarily normalized; if not
                      |   |   |            | qualified, the scheme will be
                      |   |   |            | guessed
  identifierType      | Y | Y | str        | identifier scheme, e.g.,
                      |   |   |            | "ARK", upper- or lowercase
  owner               | Y | Y | str        | username
  ownergroup          | Y | Y | str        | groupname
  createTime          |   | Y | (int, int) | time range as pair of Unix
                      |   |   |            | timestamps; bounds are
                      |   |   |            | inclusive; either/both bounds
                      |   |   |            | may be None
  updateTime          |   | Y | (int, int) | ditto
  status              | Y | Y | str        | status display value, e.g.,
                      |   |   |            | "public"
  exported            |   | Y | bool       |
  crossref            |   |   | bool       | True if the identifier is
                      |   |   |            | registered with CrossRef
  target              |   |   | str        | URL
  profile             | Y | Y | str        | profile label, e.g., "erc"
  isTest              |   | Y | bool       |
  resourceCreator     |   | Y | str        | limited fulltext-style boolean
                      |   |   |            | expression, e.g.,
                      |   |   |            | '"green eggs" ham'
  resourceTitle       |   | Y | str        | ditto
  resourcePublisher   |   | Y | str        | ditto
  keywords            |   |   | str        | ditto
  resourcePublica-    |   | Y | (int, int) | time range as pair of years;
    tionYear          |   |   |            | bounds are inclusive; either/
                      |   |   |            | both bounds may be None
  resourceType        | Y | Y | str        | general resource type, e.g.,
                      |   |   |            | "Image"
  hasMetadata         |   | Y | bool       |
  publicSearchVisible |   | Y | bool       |
  hasIssues           |   | Y | bool       |
  -------------------------------------------------------------------------

  'constraints' must include one or more of: an owner constraint, an
  ownergroup constraint, or a publicSearchVisible=True constraint; if
  not, an assertion error is raised.  Otherwise, this function is
  forgiving, and will produce a QuerySet even if constraint values are
  nonsensical.
  """
  filters = []
  scopeRequirementMet = False
  for column, value in constraints.items():
    if column in ["exported", "isTest", "hasMetadata", "publicSearchVisible",
      "hasIssues"]:
      filters.append(django.db.models.Q(**{ column: value }))
      if column == "publicSearchVisible" and value == True:
        scopeRequirementMet = True
    elif column == "identifier":
      v = util.validateIdentifier(value)
      if v == None:
        if re.match("\d{5}/", value):
          v = util.validateArk(value)
          if v != None: v = "ark:/" + v
        elif re.match("10\.[1-9]\d{3,4}/", value):
          v = util.validateDoi(value)
          if v != None: v = "doi:" + v
        if v == None: v = value
      filters.append(django.db.models.Q(identifier__startswith=v))
    elif column == "identifierType":
      if isinstance(value, basestring): value = [value]
      filters.append(reduce(operator.or_,
        [django.db.models.Q(identifier__startswith=(v.lower() + ":"))\
        for v in value]))
    elif column == "owner":
      if isinstance(value, basestring): value = [value]
      filters.append(reduce(operator.or_,
        [django.db.models.Q(owner__username=v) for v in value]))
      scopeRequirementMet = True
    elif column == "ownergroup":
      if isinstance(value, basestring): value = [value]
      filters.append(reduce(operator.or_,
        [django.db.models.Q(ownergroup__groupname=v) for v in value]))
      scopeRequirementMet = True
    elif column in ["createTime", "updateTime"]:
      if value[0] != None:
        if value[1] != None:
          filters.append(django.db.models.Q(**{ (column + "__range"): value }))
        else:
          filters.append(
            django.db.models.Q(**{ (column + "__gte"): value[0] }))
      else:
        if value[1] != None:
          filters.append(
            django.db.models.Q(**{ (column + "__lte"): value[1] }))
    elif column == "status":
      if isinstance(value, basestring): value = [value]
      filters.append(reduce(operator.or_,
        [django.db.models.Q(status=\
        ezidapp.models.Identifier.statusDisplayToCode.get(v, v))\
        for v in value]))
    elif column == "crossref":
      if value:
        filters.append(~django.db.models.Q(crossrefStatus=""))
      else:
        filters.append(django.db.models.Q(crossrefStatus=""))
    elif column == "target":
      # Unfortunately we don't store URLs in any kind of normalized
      # form, so we have no real means to take URL equivalence into
      # account.  The one thing we give flexibility on in matching is
      # the presence or absence of a trailing slash (well, that and
      # case-insensitivity.)
      values = [value]
      u = urlparse.urlparse(value)
      if u.params == "" and u.query == "" and u.fragment == "":
        # Make sure all post-path syntax is removed.
        value = u.geturl()
        if value.endswith("/"):
          values.append(value[:-1])
        else:
          values.append(value + "/")
      qlist = []
      for v in values:
        q = django.db.models.Q(searchableTarget=v[::-1][:_maxTargetLength])
        if len(v) > _maxTargetLength: q &= django.db.models.Q(target=v)
        qlist.append(q)
      filters.append(reduce(operator.or_, qlist))
    elif column == "profile":
      if isinstance(value, basestring): value = [value]
      filters.append(reduce(operator.or_,
        [django.db.models.Q(profile__label=v) for v in value]))
    elif column in ["resourceCreator", "resourceTitle", "resourcePublisher",
      "keywords"]:
      if _fulltextSupported:
        # MySQL interprets some characters as operators, and will
        # return an error if a query is malformed according to its
        # less-than-well-defined rules.  For safety we remove all
        # operators that are outside double quotes (i.e., quotes are
        # the only operator we retain).
        v = ""
        inQuote = False
        for c in value:
          if c == '"':
            inQuote = not inQuote
          else:
            if not inQuote and not c.isalnum(): c = " "
          v += c
        if inQuote: v += '"'
        filters.append(django.db.models.Q(**{ (column + "__search"): v }))
      else:
        value = value.split()
        if len(value) > 0:
          filters.append(reduce(operator.or_,
            [django.db.models.Q(**{ (column + "__icontains"): v })\
            for v in value]))
    elif column == "resourcePublicationYear":
      if value[0] != None:
        if value[1] != None:
          if value[0] == value[1]:
            filters.append(
              django.db.models.Q(searchablePublicationYear=value[0]))
          else:
            filters.append(django.db.models.Q(
              searchablePublicationYear__range=value))
        else:
          filters.append(
            django.db.models.Q(searchablePublicationYear__gte=value[0]))
      else:
        if value[1] != None:
          filters.append(
            django.db.models.Q(searchablePublicationYear__lte=value[1]))
    elif column == "resourceType":
      if isinstance(value, basestring): value = [value]
      filters.append(reduce(operator.or_,
        [django.db.models.Q(searchableResourceType=\
        ezidapp.models.validation.resourceTypes.get(v, v)) for v in value]))
    else:
      assert False, "unrecognized column"
  assert scopeRequirementMet, "query scope requirement not met"
  qs = ezidapp.models.SearchIdentifier.objects.filter(*filters)
  if len(selectRelated) > 0: qs = qs.select_related(*selectRelated)
  if len(defer) > 0: qs = qs.defer(*defer)
  if orderBy != None:
    prefix = ""
    if orderBy.startswith("-"):
      prefix = "-"
      orderBy = orderBy[1:]
    if orderBy in ["identifier", "createTime", "updateTime", "status",
      "exported", "isTest", "hasMetadata", "publicSearchVisible"]:
      pass
    elif orderBy == "identifierType":
      orderBy = "identifier"
    elif orderBy == "owner":
      orderBy = "owner__username"
    elif orderBy == "ownergroup":
      orderBy = "ownergroup__groupname"
    elif orderBy == "profile":
      orderBy = "profile__label"
    elif orderBy == "resourceCreator":
      orderBy = "resourceCreatorPrefix"
    elif orderBy == "resourceTitle":
      orderBy = "resourceTitlePrefix"
    elif orderBy == "resourcePublisher":
      orderBy = "resourcePublisherPrefix"
    elif orderBy == "resourcePublicationYear":
      orderBy = "searchablePublicationYear"
    elif orderBy == "resourceType":
      orderBy = "searchableResourceType"
    else:
      assert False, "column does not support ordering"
    qs = qs.order_by(prefix + orderBy)
  return qs
