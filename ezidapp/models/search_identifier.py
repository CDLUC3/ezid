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

_profileCache = None

def clearProfileCache ():
  global _profileCache
  _profileCache = None

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
    global _profileCache
    import util2
    if _profileCache == None:
      _profileCache = dict((p.label, p) for p in\
        search_profile.SearchProfile.objects.all())
    return _profileCache[util2.defaultProfile(self.identifier)]

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
