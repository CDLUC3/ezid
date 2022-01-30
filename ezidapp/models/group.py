#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Object Relational Mapper (ORM) models for groups
"""
import re

import django.apps
import django.core.validators
import django.db.models
import ezidapp.models.shoulder

import ezidapp.models.realm
import ezidapp.models.validation
import impl.log
import impl.nog.minter
import impl.util


class Group(django.db.models.Model):
    """An EZID group, which typically corresponds to a paying account or
    institution.
    """

    class Meta:
        verbose_name = "group"
        verbose_name_plural = "groups"

    def clean(self):
        if self.pid == "":
            try:
                #agent_model = django.apps.apps.get_model('ezidapp', 'getAgentShoulder')
                agent_model = ezidapp.models.shoulder.getAgentShoulder()
                assert agent_model.isArk, "Agent shoulder type must be ARK"
                self.pid = "{}{}".format(agent_model.prefix, impl.nog.minter.mint_id(agent_model))
            except Exception as e:
                impl.log.otherError("group.Group.clean", e)
                raise

        if self.groupname == "anonymous":
            raise django.core.validators.ValidationError(
                {"groupname": "The name 'anonymous' is reserved."}
            )
        self.organizationName = self.organizationName.strip()
        self.organizationAcronym = self.organizationAcronym.strip()
        self.organizationStreetAddress = self.organizationStreetAddress.strip()
        self.notes = self.notes.strip()

    def __str__(self):
        return f"{self.groupname} ({self.organizationName})"

    @property
    def users(self):
        # Returns a Django related manager for the set of users in this
        # group.
        return self.user_set

    # The group's persistent identifier, e.g., "ark:/99166/foo". The field will in practice never
    # be empty; rather, if empty, a new persistent identifier is minted (but not created).
    #
    # The uniqueness requirement is actually stronger than indicated here: it is expected that all
    # agent (i.e., all user and group) persistent identifiers are unique.
    pid = django.db.models.CharField(
        max_length=impl.util.maxIdentifierLength,
        unique=True,
        validators=[ezidapp.models.validation.agentPidOrEmpty],
    )

    # The group's groupname, e.g., "dryad".
    groupname = django.db.models.CharField(
        max_length=32,
        unique=True,
        validators=[
            django.core.validators.RegexValidator(
                "^[a-z0-9]+([-_.][a-z0-9]+)*$", "Invalid groupname.", flags=re.I
            )
        ],
    )

    # The group's realm.
    realm = django.db.models.ForeignKey('ezidapp.Realm', on_delete=django.db.models.PROTECT)

    # An EZID group is typically associated with some type of
    # organization, institution, or group; these fields describe that
    # entity.
    organizationName = django.db.models.CharField(
        "name", max_length=255, validators=[ezidapp.models.validation.nonEmpty]
    )
    organizationAcronym = django.db.models.CharField("acronym", max_length=255, blank=True)
    organizationUrl = django.db.models.URLField("URL", max_length=255)
    organizationStreetAddress = django.db.models.CharField(
        "street address",
        max_length=255,
        validators=[ezidapp.models.validation.nonEmpty],
    )

    # Fields for business purposes only; not used by EZID.
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

    # Deprecated and not used at present. (Former usage: Determines if users in the group may
    # register identifiers with Crossref.
    #
    # Crossref registration requires the enablement of both the user and the shoulder.)
    crossrefEnabled = django.db.models.BooleanField("Crossref enabled", default=False)

    # The shoulders to which users in the group have access. The test
    # shoulders are not included in this relation.
    shoulders = django.db.models.ManyToManyField('ezidapp.Shoulder', blank=True)

    # Any additional notes.
    notes = django.db.models.TextField(blank=True)

    # See below.
    isAnonymous = False


class AnonymousGroup(object):
    """The group in which the anonymous user resides.

    This class can be used directly. An object need not be instantiated.
    """
    pid = "anonymous"
    groupname = "anonymous"
    realm = ezidapp.models.realm.AnonymousRealm
    # realm = 'ezidapp.AnonymousRealm'
    crossrefEnabled = False

    class inner(object):
        def all(self):
            return []

    shoulders = inner()
    users = inner()
    isAnonymous = True
