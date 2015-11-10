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

  resourcePublicationDate = django.db.models.CharField(max_length=10,
    editable=False)
  # Computed value: the resource's publication date, if available, as
  # mapped from the identifier's preferred metadata profile;
  # otherwise, empty.  A nonempty publication date may take one of
  # three forms: YYYY, YYYY-MM, or YYYY-MM-DD.

  resourceType = django.db.models.CharField(max_length=1, editable=False,
    choices=sorted([(v, k) for k, v in validation.resourceTypes.items()],
    cmp=lambda a, b: cmp(a[1], b[1])))
  # Computed value: the resource's type, if available, as mapped from
  # the identifier's preferred metadata profile; otherwise, empty.
  # The type is stored as a single-character mnemonic code.

  keywords = django.db.models.TextField(editable=False)
  # Computed value: a compendium of all searchable text.

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
    self.resourceCreator = ""
    self.resourceTitle = ""
    self.resourcePublisher = ""
    self.resourcePublicationDate = ""
    self.resourceType = ""
    km = mapping.map(self.cm, profile=self.profile.label)
    if km.creator != None: self.resourceCreator = km.creator
    if km.title != None: self.resourceTitle = km.title
    if km.publisher != None: self.resourcePublisher = km.publisher
    d = km.validatedDate
    if d != None: self.resourcePublicationDate = d
    t = km.validatedType
    if t != None: self.resourceType = validation.resourceTypes[t.split("/")[0]]
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
      # public search
      ("publicSearchVisible", "resourcePublicationDate"),
      ("publicSearchVisible", "resourceType"),
      # user management search
      ("owner", "resourcePublicationDate"),
      ("owner", "resourceType"),
      ("owner", "createTime"),
      ("owner", "updateTime"),
      ("owner", "status"),
      ("owner", "exported"),
      ("owner", "hasMetadata"),
      ("ownergroup", "resourcePublicationDate"),
      ("ownergroup", "resourceType"),
      ("ownergroup", "createTime"),
      ("ownergroup", "updateTime"),
      ("ownergroup", "status"),
      ("ownergroup", "exported"),
      ("ownergroup", "hasMetadata"),
      # dashboard
      ("owner", "hasIssues"),
      ("ownergroup", "hasIssues"),
      # batch download
      ("owner", "identifier"),
      ("ownergroup", "identifier"),
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
    if not insertOnMissing:
      raise model.DoesNotExist("No %s for %s='%s'." % (model.__name__,
        attribute, key))
    try:
      i = model(**{ attribute: key })
      i.full_clean(validate_unique=False)
      i.save()
    except django.db.utils.IntegrityError:
      # Somebody beat us to it.
      i = model.objects.get(**{ attribute: key })
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
  i = SearchIdentifier(identifier)
  i.fromLegacy(metadata)
  i.owner = _getUser(metadata["_o"])
  i.ownergroup = _getGroup(metadata["_g"])
  i.profile = _getProfile(metadata["_p"])
  if i.isDoi: i.datacenter = _getDatacenter(metadata["_d"])
  i.my_full_clean()
  i.save(force_insert=forceInsert, force_update=forceUpdate)
