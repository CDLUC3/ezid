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

import django.core.validators
import django.db.models

import ezidapp.models.group
import ezidapp.models.shoulder
import ezidapp.models.store_realm
import ezidapp.models.validation


class StoreGroup(ezidapp.models.group.Group):

    # Inherited foreign key declarations...
    realm = django.db.models.ForeignKey(
        ezidapp.models.store_realm.StoreRealm, on_delete=django.db.models.PROTECT
    )

    organizationName = django.db.models.CharField(
        "name", max_length=255, validators=[ezidapp.models.validation.nonEmpty]
    )
    organizationAcronym = django.db.models.CharField(
        "acronym", max_length=255, blank=True
    )
    organizationUrl = django.db.models.URLField("URL", max_length=255)
    organizationStreetAddress = django.db.models.CharField(
        "street address",
        max_length=255,
        validators=[ezidapp.models.validation.nonEmpty],
    )
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
    accountType = django.db.models.CharField(
        "account type",
        max_length=1,
        choices=[
            (BACHELORS, "Associate/bachelors-granting"),
            (CORPORATE, "Corporate"),
            (GROUP, "Group"),
            (INSTITUTION, "Institution"),
            (MASTERS, "Masters-granting"),
            (NONPAYING, "Non-paying"),
            (SERVICE, "Service"),
        ],
        blank=True,
    )
    agreementOnFile = django.db.models.BooleanField("agreement on file", default=False)
    # Fields for business purposes only; not used by EZID.

    crossrefEnabled = django.db.models.BooleanField("Crossref enabled", default=False)
    # Deprecated and not used at present.  (Former usage:
    # Determines if users in the group may register identifiers with
    # Crossref.  Note that Crossref registration requires the enablement
    # of both the user and the shoulder.)

    shoulders = django.db.models.ManyToManyField(
        ezidapp.models.shoulder.Shoulder, blank=True
    )
    # The shoulders to which users in the group have access.  The test
    # shoulders are not included in this relation.

    notes = django.db.models.TextField(blank=True)
    # Any additional notes.

    @property
    def users(self):
        # Returns a Django related manager for the set of users in this
        # group.
        return self.storeuser_set

    def clean(self):
        super(StoreGroup, self).clean()
        if self.groupname == "anonymous":
            raise django.core.validators.ValidationError(
                {"groupname": "The name 'anonymous' is reserved."}
            )
        self.organizationName = self.organizationName.strip()
        self.organizationAcronym = self.organizationAcronym.strip()
        self.organizationStreetAddress = self.organizationStreetAddress.strip()
        self.notes = self.notes.strip()

    class Meta:
        verbose_name = "group"
        verbose_name_plural = "groups"

    def __str__(self):
        return f"{self.groupname} ({self.organizationName})"

    isAnonymous = False
    # See below.


# The following caches are only added to or replaced entirely;
# existing entries are never modified.  Thus, with appropriate coding
# below, they are threadsafe without needing locking.

_caches = None  # (pidCache, groupnameCache, idCache)


def clearCaches():
    global _caches
    _caches = None


def _databaseQuery():
    return StoreGroup.objects.select_related("realm").prefetch_related("shoulders")


def _getCaches():
    global _caches
    caches = _caches
    if caches is None:
        pidCache = dict((g.pid, g) for g in _databaseQuery().all())
        groupnameCache = dict((g.groupname, g) for g in list(pidCache.values()))
        idCache = dict((g.id, g) for g in list(pidCache.values()))
        caches = (pidCache, groupnameCache, idCache)
        _caches = caches
    return caches


def getGroupByPid(pid):
    # Returns the group identified by persistent identifier 'pid', or
    # None if there is no such group.  AnonymousGroup is returned in
    # response to "anonymous".
    if pid == "anonymous":
        return AnonymousGroup
    pidCache, groupnameCache, idCache = _getCaches()
    if pid not in pidCache:
        try:
            g = _databaseQuery().get(pid=pid)
        except StoreGroup.DoesNotExist:
            return None
        pidCache[pid] = g
        groupnameCache[g.groupname] = g
        idCache[g.id] = g
    return pidCache[pid]


def getGroupByGroupname(groupname):
    # Returns the group identified by local name 'groupname', or None if
    # there is no such group.  AnonymousGroup is returned in response to
    # "anonymous".
    if groupname == "anonymous":
        return AnonymousGroup
    pidCache, groupnameCache, idCache = _getCaches()
    if groupname not in groupnameCache:
        try:
            g = _databaseQuery().get(groupname=groupname)
        except StoreGroup.DoesNotExist:
            return None
        pidCache[g.pid] = g
        groupnameCache[groupname] = g
        idCache[g.id] = g
    return groupnameCache[groupname]


def getProfileById(id_str):
    # Returns the group identified by internal identifier 'id', or None
    # if there is no such group.
    pidCache, groupnameCache, idCache = _getCaches()
    if id_str not in idCache:
        try:
            g = _databaseQuery().get(id=id_str)
        except StoreGroup.DoesNotExist:
            return None
        pidCache[g.pid] = g
        groupnameCache[g.groupname] = g
        idCache[id_str] = g
    return idCache[id_str]


class AnonymousGroup(object):
    # A class to represent the group in which the anonymous user
    # resides.  Note that this class can be used directly--- an object
    # need not be instantiated.
    pid = "anonymous"
    groupname = "anonymous"
    realm = ezidapp.models.store_realm.AnonymousRealm
    crossrefEnabled = False

    class inner(object):
        def all(self):
            return []

    shoulders = inner()
    users = inner()
    isAnonymous = True
