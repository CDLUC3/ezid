# =============================================================================
#
# EZID :: ezidapp/models/store_group.py
#
# Database model for groups in the store database.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2016, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.db.models

import group
import shoulder
import store_realm
import validation

class StoreGroup (group.Group):

  # Inherited foreign key declarations...
  realm = django.db.models.ForeignKey(store_realm.StoreRealm,
    on_delete=django.db.models.PROTECT)

  organizationName = django.db.models.CharField("name", max_length=255,
    validators=[validation.nonEmpty])
  organizationAcronym = django.db.models.CharField("acronym", max_length=255,
    blank=True)
  organizationUrl = django.db.models.URLField("URL", max_length=255)
  organizationStreetAddress = django.db.models.CharField("street address",
    max_length=255, validators=[validation.nonEmpty])
  # An EZID group is typically associated with some type of
  # organization, institution, or group; these fields describe that
  # entity.

  BACHELORS = "B"
  CORPORATE = "C"
  GROUP = "G"
  INSTITUTION = "I"
  MASTERS = "M"
  NONPAYING = "N"
  SERVICE = "S"
  accountType = django.db.models.CharField("account type", max_length=1,
    choices=[(BACHELORS, "Associate/bachelors-granting"),
    (CORPORATE, "Corporate"), (GROUP, "Group"),
    (INSTITUTION, "Institution"), (MASTERS, "Masters-granting"),
    (NONPAYING, "Non-paying"), (SERVICE, "Service")], blank=True)
  agreementOnFile = django.db.models.BooleanField("agreement on file",
    default=False)
  # Fields for business purposes only; not used by EZID.

  crossrefEnabled = django.db.models.BooleanField("CrossRef enabled",
    default=False)
  # Determines if users in the group may register identifiers with
  # CrossRef.  Note that CrossRef registration requires the enablement
  # of both the user and the shoulder.

  shoulders = django.db.models.ManyToManyField(shoulder.Shoulder, blank=True)
  # The shoulders to which users in the group have access.  The test
  # shoulders are not included in this relation.

  notes = django.db.models.TextField(blank=True)
  # Any additional notes.

  def clean (self):
    super(StoreGroup, self).clean()
    self.organizationName = self.organizationName.strip()
    self.organizationAcronym = self.organizationAcronym.strip()
    self.organizationStreetAddress = self.organizationStreetAddress.strip()
    self.notes = self.notes.strip()

  class Meta:
    verbose_name = "group"
    verbose_name_plural = "groups"

  def __unicode__ (self):
    return "%s (%s)" % (self.groupname, self.organizationName)

# The following caches are only added to or replaced entirely;
# existing entries are never modified.  Thus, with appropriate coding
# below, they are threadsafe without needing locking.

_caches = None # (pidCache, groupnameCache)

def clearCaches ():
  global _caches
  _caches = None

def _getCaches ():
  global _caches
  caches = _caches
  if caches == None:
    pidCache = dict((g.pid, g) for g in StoreGroup.objects\
      .select_related("realm").prefetch_related("shoulders").all())
    groupnameCache = dict((g.groupname, g) for g in pidCache.values())
    caches = (pidCache, groupnameCache)
    _caches = caches
  return caches

def getByPid (pid):
  # Returns the group identified by persistent identifier 'pid', or
  # None if there is no such group.
  pidCache, groupnameCache = _getCaches()
  if pid not in pidCache:
    try:
      g = StoreGroup.objects\
        .select_related("realm").prefetch_related("shoulders").get(pid=pid)
    except StoreGroup.DoesNotExist:
      return None
    pidCache[pid] = g
    groupnameCache[g.groupname] = g
  return pidCache[pid]

def getByGroupname (groupname):
  # Returns the group identified by local name 'groupname', or None if
  # there is no such group.
  pidCache, groupnameCache = _getCaches()
  if groupname not in groupnameCache:
    try:
      g = StoreGroup.objects.select_related("realm").\
        prefetch_related("shoulders").get(groupname=groupname)
    except StoreGroup.DoesNotExist:
      return None
    pidCache[g.pid] = g
    groupnameCache[groupname] = g
  return groupnameCache[groupname]
