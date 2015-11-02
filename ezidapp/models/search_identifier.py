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

# Deferred imports...
"""
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

  keywords = django.db.models.TextField(editable=False)
  # Computed value: a compendium of all searchable text.

  def computeComputedValues (self):
    super(SearchIdentifier, self).computeComputedValues()
    v = [self.identifier, self.owner.username, self.ownergroup.groupname]
    if self.isDoi: v.append(self.datacenter.symbol)
    if self.target != self.defaultTarget: v.append(self.target)
    v.extend(self.cm.values())
    self.keywords = " ; ".join(v)

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
      ("owner", "export"),
      ("owner", "hasMetadata"),
      ("ownergroup", "resourcePublicationDate"),
      ("ownergroup", "resourceType"),
      ("ownergroup", "createTime"),
      ("ownergroup", "updateTime"),
      ("ownergroup", "status"),
      ("ownergroup", "export"),
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
