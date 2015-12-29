# =============================================================================
#
# EZID :: ezidapp/models/search_identifier.py
#
# Database model for identifiers in the search database.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.db.models
import django.db.utils

import custom_fields
import identifier
import search_datacenter
import search_group
import search_profile
import search_user
import util
import validation

# Deferred imports...
"""
import mapping
import util2
"""

class SearchIdentifier (identifier.Identifier):
  # An identifier as stored in the search database.

  # Foreign key declarations.  Note that in the search database every
  # identifier has an owner; anonymous identifiers are not stored.
  # For performance we do not validate foreign key references (but of
  # course they're still checked in the database).

  owner = custom_fields.NonValidatingForeignKey(search_user.SearchUser,
    on_delete=django.db.models.PROTECT)
  ownergroup = custom_fields.NonValidatingForeignKey(search_group.SearchGroup,
    blank=True, null=True, default=None, on_delete=django.db.models.PROTECT)
  datacenter = custom_fields.NonValidatingForeignKey(
    search_datacenter.SearchDatacenter, blank=True, null=True,
    default=None, on_delete=django.db.models.PROTECT)
  profile = custom_fields.NonValidatingForeignKey(search_profile.SearchProfile,
    blank=True, null=True, default=None, on_delete=django.db.models.PROTECT)

  @property
  def defaultProfile (self):
    import util2
    return _getProfile(util2.defaultProfile(self.identifier))

  searchableTarget = django.db.models.CharField(max_length=255,
    editable=False)
  # Computed value.  To support searching over target URLs (which are
  # too long to be fully indexed), this field is the last 255
  # characters of the target URL in reverse order.

  # Citation metadata follows.  Which is to say, the following
  # metadata refers to the resource identified by the identifier, not
  # the identifier itself.

  resourceCreator = django.db.models.TextField(editable=False)
  # Computed value: the resource's creator, if available, as mapped
  # from the identifier's preferred metadata profile; otherwise,
  # empty.

  resourceTitle = django.db.models.TextField(editable=False)
  # Computed value: the resource's title, if available, as mapped from
  # the identifier's preferred metadata profile; otherwise, empty.

  resourcePublisher = django.db.models.TextField(editable=False)
  # Computed value: the resource's publisher, if available, as mapped
  # from the identifier's preferred metadata profile; otherwise,
  # empty.

  resourcePublicationDate = django.db.models.TextField(editable=False)
  # Computed value: the resource's publication date, if available, as
  # mapped from the identifier's preferred metadata profile;
  # otherwise, empty.

  searchablePublicationYear = django.db.models.IntegerField(
    blank=True, null=True, editable=False)
  # The year portion of resourcePublicationDate, as a numeric, if one
  # could be extracted; otherwise, None.

  resourceType = django.db.models.TextField(editable=False)
  # Computed value: the resource's type, if available, as mapped from
  # the identifier's preferred metadata profile; otherwise, empty.

  searchableResourceType = django.db.models.CharField(max_length=2,
    editable=False,
    choices=sorted([(v, k) for k, v in validation.resourceTypes.items()],
    cmp=lambda a, b: cmp(a[1], b[1])))
  # The general resource type stored as a single-character mnemonic
  # code, if one could be extracted from resourceType; otherwise,
  # empty.

  keywords = django.db.models.TextField(editable=False)
  # Computed value: a compendium of all searchable text.

  # To support (partial) ordering by resource creator/title/publisher,
  # which have unbounded length and are therefore unindexable, we add
  # the following fields that hold prefixes of the corresponding
  # fields above.

  indexedPrefixLength = 50

  resourceCreatorPrefix = django.db.models.CharField(
    max_length=indexedPrefixLength, editable=False)
  resourceTitlePrefix = django.db.models.CharField(
    max_length=indexedPrefixLength, editable=False)
  resourcePublisherPrefix = django.db.models.CharField(
    max_length=indexedPrefixLength, editable=False)

  hasMetadata = django.db.models.BooleanField(editable=False)
  # Computed value: True if resourceTitle and resourcePublicationDate
  # are nonempty, and at least one of resourceCreator and
  # resourcePublisher is nonempty (i.e., the identifier has at least
  # who/what/when metadata in ERC parlance).

  publicSearchVisible = django.db.models.BooleanField(editable=False)
  # Computed value: True if the identifier is visible in EZID's public
  # search interface, i.e., if the identifier is public and exported
  # and not a test identifier.

  oaiVisible = django.db.models.BooleanField(editable=False)
  # Computed value: True if the identifier is visible in the OAI feed,
  # i.e., if the identifier is public and exported and not a test
  # identifier (i.e., if publicSearchVisible is True), and if
  # hasMetadata is True and if the target URL is not the default
  # target URL.

  hasIssues = django.db.models.BooleanField(editable=False)
  # Computed value: True if the identifier "has issues," i.e., has
  # problems of some kind.

  def issueReasons (self):
    # Returns a list of the identifier's issues.
    reasons = []
    if not self.hasMetadata: reasons.append("missing metadata")
    if self.isCrossrefBad:
      reasons.append("CrossRef registration " +\
        ("warning" if self.crossrefStatus == self.CR_WARNING else "failure"))
    return reasons

  def computeComputedValues (self):
    super(SearchIdentifier, self).computeComputedValues()
    import mapping
    self.searchableTarget = self.target[::-1]\
      [:self._meta.get_field("searchableTarget").max_length]
    self.resourceCreator = ""
    self.resourceTitle = ""
    self.resourcePublisher = ""
    self.resourcePublicationDate = ""
    self.resourceType = ""
    km = mapping.map(self.cm, profile=self.profile.label)
    if km.creator != None: self.resourceCreator = km.creator
    if km.title != None: self.resourceTitle = km.title
    if km.publisher != None: self.resourcePublisher = km.publisher
    if km.date != None: self.resourcePublicationDate = km.date
    d = km.validatedDate
    if d != None:
      self.searchablePublicationYear = int(d[:4])
    else:
      self.searchablePublicationYear = None
    if km.type != None: self.resourceType = km.type
    t = km.validatedType
    if t != None:
      self.searchableResourceType = validation.resourceTypes[t.split("/")[0]]
    else:
      self.searchableResourceType = ""
    kw = [self.identifier, self.owner.username, self.ownergroup.groupname]
    if self.isDoi: kw.append(self.datacenter.symbol)
    if self.target != self.defaultTarget: kw.append(self.target)
    for k, v in self.cm.items():
      if k in ["datacite", "crossref"]:
        try:
          kw.append(util.extractXmlContent(v))
        except:
          kw.append(v)
      else:
        kw.append(v)
    self.keywords = " ; ".join(kw)
    self.resourceCreatorPrefix =\
      self.resourceCreator[:self.indexedPrefixLength]
    self.resourceTitlePrefix = self.resourceTitle[:self.indexedPrefixLength]
    self.resourcePublisherPrefix =\
      self.resourcePublisher[:self.indexedPrefixLength]
    self.hasMetadata = self.resourceTitle != "" and\
      self.resourcePublicationDate != "" and (self.resourceCreator != "" or\
      self.resourcePublisher != "")
    self.publicSearchVisible = self.isPublic and self.exported and\
      not self.isTest
    self.oaiVisible = self.publicSearchVisible and self.hasMetadata and\
      self.target != self.defaultTarget
    self.hasIssues = not self.hasMetadata or self.isCrossrefBad

  # Note that MySQL FULLTEXT indexes must be created outside Django;
  # see .../etc/search-mysql-addendum.sql.

  class Meta (identifier.Identifier.Meta):
    index_together = [
      # batch download and management search
      ("owner", "identifier"),
      ("ownergroup", "identifier"),
      # management search
      ("owner", "createTime"),
      ("owner", "updateTime"),
      ("owner", "status"),
      ("owner", "exported"),
      ("owner", "crossrefStatus"),
      ("owner", "profile"),
      ("owner", "isTest"),
      ("owner", "searchablePublicationYear"),
      ("owner", "searchableResourceType"),
      ("owner", "hasMetadata"),
      ("owner", "hasIssues"),
      ("owner", "resourceCreatorPrefix"),
      ("owner", "resourceTitlePrefix"),
      ("owner", "resourcePublisherPrefix"),
      ("ownergroup", "createTime"),
      ("ownergroup", "updateTime"),
      ("ownergroup", "status"),
      ("ownergroup", "exported"),
      ("ownergroup", "crossrefStatus"),
      ("ownergroup", "profile"),
      ("ownergroup", "isTest"),
      ("ownergroup", "searchablePublicationYear"),
      ("ownergroup", "searchableResourceType"),
      ("ownergroup", "hasMetadata"),
      ("ownergroup", "hasIssues"),
      ("ownergroup", "resourceCreatorPrefix"),
      ("ownergroup", "resourceTitlePrefix"),
      ("ownergroup", "resourcePublisherPrefix"),
      # public search
      ("publicSearchVisible", "identifier"),
      ("publicSearchVisible", "createTime"),
      ("publicSearchVisible", "updateTime"),
      ("publicSearchVisible", "searchablePublicationYear"),
      ("publicSearchVisible", "searchableResourceType"),
      ("publicSearchVisible", "resourceCreatorPrefix"),
      ("publicSearchVisible", "resourceTitlePrefix"),
      ("publicSearchVisible", "resourcePublisherPrefix"),
      # general search
      ("searchableTarget",),
      # OAI
      ("oaiVisible", "updateTime")
    ]

# The following caches are only added to or replaced entirely;
# existing entries are never modified.  Thus, with appropriate coding
# below, they are threadsafe without needing locking.

_userCache = None
_groupCache = None
_datacenterCache = None
_profileCache = None

def clearCaches ():
  global _userCache, _groupCache, _datacenterCache, _profileCache
  _userCache = None
  _groupCache = None
  _datacenterCache = None
  _profileCache = None

def _getFromCache (cache, model, attribute, key, insertOnMissing=True):
  # Generic caching function supporting the caches in this module.
  # Returns (I, cache) where I is the instance of 'model' for which
  # I.'attribute' = 'key'.  'cache' may be None on input, and it is
  # possibly set and/or augmented on return.
  if cache == None:
    cache = dict((getattr(i, attribute), i) for i in model.objects.all())
  if key in cache:
    i = cache[key]
  else:
    if insertOnMissing:
      try:
        i = model(**{ attribute: key })
        i.full_clean(validate_unique=False)
        i.save()
      except django.db.utils.IntegrityError:
        # Somebody beat us to it.
        i = model.objects.get(**{ attribute: key })
    else:
      try:
        i = model.objects.get(**{ attribute: key })
      except model.DoesNotExist:
        raise model.DoesNotExist("No %s for %s='%s'." % (model.__name__,
          attribute, key))
    cache[key] = i
  return i, cache

def _getUser (pid):
  global _userCache
  u, _userCache = _getFromCache(_userCache, search_user.SearchUser,
    "pid", pid, insertOnMissing=False)
  return u

def _getGroup (pid):
  global _groupCache
  g, _groupCache = _getFromCache(_groupCache, search_group.SearchGroup,
    "pid", pid, insertOnMissing=False)
  return g

def _getDatacenter (symbol):
  global _datacenterCache
  d, _datacenterCache = _getFromCache(_datacenterCache,
    search_datacenter.SearchDatacenter, "symbol", symbol)
  return d

def _getProfile (label):
  global _profileCache
  p, _profileCache = _getFromCache(_profileCache, search_profile.SearchProfile,
    "label", label)
  return p

def updateFromLegacy (identifier, metadata, forceInsert=False,
  forceUpdate=False):
  # Inserts or updates an identifier in the search database.  The
  # identifier is constructed from a legacy representation.
  i = SearchIdentifier(identifier=identifier)
  i.fromLegacy(metadata)
  i.owner = _getUser(metadata["_o"])
  i.ownergroup = _getGroup(metadata["_g"])
  i.profile = _getProfile(metadata["_p"])
  if i.isDoi: i.datacenter = _getDatacenter(metadata["_d"])
  i.my_full_clean()
  # Because backproc.py's call to this function is really the only
  # place identifiers get inserted and updated in the search database,
  # we're not concerned with race conditions.
  if not forceInsert:
    j = SearchIdentifier.objects.filter(identifier=identifier).only("id")
    if len(j) > 0: i.id = j[0].id
  i.save(force_insert=forceInsert, force_update=forceUpdate)
