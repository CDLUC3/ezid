# =============================================================================
#
# EZID :: ezidapp/models/group.py
#
# Abstract database model for groups.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import re

import django.apps
import django.core.validators
import django.core.validators
import django.db.models
import django.db.models

import ezidapp.models.validation
import ezidapp.models.validation
import impl.log
import impl.nog.minter
import impl.util


class Group(django.db.models.Model):
    # An EZID group, which typically corresponds to a paying account or
    # institution.

    class Meta:
        abstract = True

    pid = django.db.models.CharField(
        max_length=impl.util.maxIdentifierLength,
        unique=True,
        validators=[ezidapp.models.validation.agentPidOrEmpty],
    )
    # The group's persistent identifier, e.g., "ark:/99166/foo".  The
    # field will in practice never be empty; rather, if empty, a new
    # persistent identifier is minted (but not created).  Note that the
    # uniqueness requirement is actually stronger than indicated here:
    # it is expected that all agent (i.e., all user and group)
    # persistent identifiers are unique.

    groupname = django.db.models.CharField(
        max_length=32,
        unique=True,
        validators=[
            django.core.validators.RegexValidator(
                "^[a-z0-9]+([-_.][a-z0-9]+)*$", "Invalid groupname.", flags=re.I
            )
        ],
    )

    # The group's groupname, e.g., "dryad".

    # A note on foreign keys: since the store and search databases are
    # completely separate, foreign keys must reference different target
    # models, and so the declaration of all foreign keys is deferred to
    # the concrete subclasses.  There appears to be no better way to
    # model this in Django.

    # realm = django.db.models.ForeignKey(realm.Realm)
    # The group's realm.

    def clean(self):
        if self.pid == "":
            try:
                agent_model = django.apps.apps.get_model('ezidapp', 'getAgentShoulder')
                assert agent_model.isArk, "Agent shoulder type must be ARK"
                self.pid = "{}{}".format(
                    agent_model.prefix, impl.nog.minter.mint_id(agent_model)
                )
            except Exception as e:
                impl.log.otherError("group.Group.clean", e)
                raise

    def __str__(self):
        return self.groupname




class SearchGroup(Group):
    realm = django.db.models.ForeignKey(
        'ezidapp.SearchRealm', on_delete=django.db.models.PROTECT
    )


class StoreGroup(Group):
    # Inherited foreign key declarations...
    realm = django.db.models.ForeignKey(
        'ezidapp.StoreRealm', on_delete=django.db.models.PROTECT
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

    shoulders = django.db.models.ManyToManyField('ezidapp.Shoulder', blank=True)
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

# _caches = None  # (pidCache, groupnameCache, idCache)
#
#
# def clearCaches():
#     global _caches
#     _caches = None
#

# def _getCaches():
#     global _caches
#     caches = _caches
#     if caches is None:
#         pidCache = dict((g.pid, g) for g in _databaseQuery().all())
#         groupnameCache = dict((g.groupname, g) for g in list(pidCache.values()))
#         idCache = dict((g.id, g) for g in list(pidCache.values()))
#         caches = (pidCache, groupnameCache, idCache)
#         _caches = caches
#     return caches


class AnonymousGroup(object):
    # A class to represent the group in which the anonymous user
    # resides.  Note that this class can be used directly--- an object
    # need not be instantiated.
    pid = "anonymous"
    groupname = "anonymous"
    # realm = ezidapp.models.realm.AnonymousRealm
    realm = 'ezidapp.AnonymousRealm'
    crossrefEnabled = False

    class inner(object):
        def all(self):
            return []

    shoulders = inner()
    users = inner()
    isAnonymous = True
