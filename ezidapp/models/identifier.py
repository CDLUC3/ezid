# =============================================================================
#
# EZID :: ezidapp/models/identifier.py
#
# Abstract database model for identifiers.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------
import pprint
import re
import time
import urllib.error
import urllib.parse
import urllib.request

import django.conf
import django.core.exceptions
import django.core.validators
import django.db
import django.db.models
import django.db.models
import django.db.utils

import ezidapp.models.custom_fields
import ezidapp.models.custom_fields
import ezidapp.models.validation
import ezidapp.models.validation
import impl.util
# import ezidapp.models.user
import impl.util
import impl.util2


# import ezidapp.models.custom_fields
# import ezidapp.models.identifier
# import ezidapp.models.datacenter
# import ezidapp.models.group
# import ezidapp.models.search_profile


def emptyDict():
    return {}


class Identifier(django.db.models.Model):
    # Describes an identifier.  This class is abstract; there are
    # separate instantiated subclasses of this class for the store and
    # search databases.

    class Meta:
        abstract = True

    identifier = django.db.models.CharField(
        max_length=impl.util.maxIdentifierLength,
        unique=True,
        validators=[ezidapp.models.validation.anyIdentifier],
    )
    # The identifier in qualified, normalized form, e.g.,
    # "ark:/12345/abc" or "doi:10.1234/ABC".

    @property
    def type(self):
        return self.identifier.split(":", 1)[0]

    @property
    def isArk(self):
        return self.identifier.startswith("ark:/")

    @property
    def isDoi(self):
        return self.identifier.startswith("doi:")

    @property
    def isUuid(self):
        return self.identifier.startswith("uuid:")

    @property
    def arkAlias(self):
        # For DOIs only, the identifier expressed in ARK syntax.
        if self.isDoi:
            return "ark:/" + impl.util.doi2shadow(self.identifier[4:])
        else:
            return None

    # A note on foreign keys: since the store and search databases are
    # completely separate, foreign keys must reference different target
    # models, and so the declaration of all foreign keys is deferred to
    # the concrete subclasses.  There appears to be no better way to
    # model this in Django.

    # owner = django.db.models.ForeignKey(user.User, blank=True, null=True)
    # The identifier's owner, or None if the owner is anonymous.

    # ownergroup = django.db.models.ForeignKey(group.Group, blank=True,
    #   null=True, default=None)
    # The identifier's owner's group, or None if the owner is anonymous.
    # If an owner is specified but not an ownergroup, the ownergroup is
    # computed.

    createTime = django.db.models.IntegerField(
        blank=True, default="", validators=[django.core.validators.MinValueValidator(0)]
    )
    # The time the identifier was created as a Unix timestamp.  If not
    # specified, the current time is used.

    updateTime = django.db.models.IntegerField(
        blank=True, default="", validators=[django.core.validators.MinValueValidator(0)]
    )
    # The time the identifier was last updated as a Unix timestamp.  If
    # not specified, the current time is used.

    RESERVED = "R"
    PUBLIC = "P"
    UNAVAILABLE = "U"
    status = django.db.models.CharField(
        max_length=1,
        choices=[
            (RESERVED, "reserved"),
            (PUBLIC, "public"),
            (UNAVAILABLE, "unavailable"),
        ],
        default=PUBLIC,
    )
    # The identifier's status.

    statusDisplayToCode = {
        "reserved": RESERVED,
        "public": PUBLIC,
        "unavailable": UNAVAILABLE,
    }

    @property
    def isReserved(self):
        return self.status == self.RESERVED

    @property
    def isPublic(self):
        return self.status == self.PUBLIC

    @property
    def isUnavailable(self):
        return self.status == self.UNAVAILABLE

    unavailableReason = django.db.models.TextField(blank=True, default="")
    # If the status is UNAVAILABLE then, optionally, a reason for the
    # unavailability, e.g., "withdrawn"; otherwise, empty.

    exported = django.db.models.BooleanField(default=True)
    # Export control: determines if the identifier is publicized by
    # exporting it to external indexing and harvesting services.
    # Although this flag may be set independently of the status, in fact
    # it has effect only if the status is public.

    # datacenter = django.db.models.ForeignKey(datacenter.Datacenter,
    #   blank=True, null=True, default=None)
    # For DataCite DOI identifiers only, the datacenter at which the
    # identifier is registered (or will be registered when the
    # identifier becomes public, in the case of a reserved identifier);
    # for Crossref DOI and non-DOI identifiers, None.

    CR_RESERVED = "R"
    CR_WORKING = "B"
    CR_SUCCESS = "S"
    CR_WARNING = "W"
    CR_FAILURE = "F"
    crossrefStatus = django.db.models.CharField(
        max_length=1,
        blank=True,
        choices=[
            (CR_RESERVED, "awaiting status change to public"),
            (CR_WORKING, "registration in progress"),
            (CR_SUCCESS, "successfully registered"),
            (CR_WARNING, "registered with warning"),
            (CR_FAILURE, "registration failure"),
        ],
        default="",
    )
    # For Crossref DOI identifiers only, indicates the status of the
    # registration process; otherwise, empty.

    # For DOI identifiers, the preceding two fields both indirectly
    # indicate the DOI registration agency: a DataCite DOI has a
    # datacenter and an empty crossrefStatus, while a Crossref DOI has
    # no datacenter and a nonempty crossrefStatus.  Someday, a true
    # registration agency field should be added.

    @property
    def isDatacite(self):
        return self.isDoi and self.crossrefStatus == ""

    @property
    def isCrossref(self):
        return self.isDoi and self.crossrefStatus != ""

    @property
    def isCrossrefGood(self):
        return self.crossrefStatus in [
            self.CR_RESERVED,
            self.CR_WORKING,
            self.CR_SUCCESS,
        ]

    @property
    def isCrossrefBad(self):
        return self.crossrefStatus in [self.CR_WARNING, self.CR_FAILURE]

    crossrefMessage = django.db.models.TextField(blank=True, default="")
    # For the CR_WARNING and CR_FAILURE Crossref statuses only, any
    # message received from Crossref; otherwise, empty.

    target = django.db.models.URLField(
        max_length=2000,
        blank=True,
        default="",
        validators=[ezidapp.models.validation.unicodeBmpOnly],
    )
    # The identifier's nominal target URL, e.g., "http://foo.com/bar".
    # (The target URL actually registered with resolvers depends on the
    # identifier's status.)  Note that EZID supplies a default target
    # URL that incorporates the identifier in it, so this field will in
    # practice never be empty.  The length limit of 2000 characters is
    # not arbitrary, but is the de facto limit accepted by most web
    # browsers.

    @property
    def defaultTarget(self):
        import impl.util2 as util2

        return util2.defaultTargetUrl(self.identifier)

    @property
    def resolverTarget(self):
        # The URL the identifier actually resolves to.
        import impl.util2 as util2

        if self.isReserved:
            return self.defaultTarget
        elif self.isUnavailable:
            return util2.tombstoneTargetUrl(self.identifier)
        else:
            return self.target

    # profile = django.db.models.ForeignKey(profile.Profile, blank=True,
    #   null=True, default=None)
    # The identifier's preferred metadata profile.  Note that there is
    # currently no constraint on profile labels, or on use of metadata
    # fields correponding to profiles.  Note that EZID supplies a
    # default profile that depends on the identifier type, so this field
    # will in practice never be None.

    # noinspection PyPropertyDefinition
    @property
    def defaultProfile(self):
        # Should return the default profile for the identifier's type;
        # must be implemented by the concrete subclass.
        assert False, "missing implementation"

    @property
    def usesCrossrefProfile(self):
        return self.profile.label == "crossref"

    @property
    def usesDataciteProfile(self):
        return self.profile.label == "datacite"

    @property
    def usesDublinCoreProfile(self):
        return self.profile.label == "dc"

    @property
    def usesErcProfile(self):
        return self.profile.label == "erc"

    cm = ezidapp.models.custom_fields.CompressedJsonField(default=emptyDict)
    # All of the identifier's citation metadata as a dictionary of
    # name/value pairs, e.g., { "erc.who": "Proust, Marcel", ... }.

    def kernelMetadata(self):
        # Returns citation metadata as a mapping.KernelMetadata object.
        # The mapping is based on the identifier's preferred metadata
        # profile.  Missing attributes will be None.
        import impl.mapping as mapping

        return mapping.map(self.cm, profile=self.profile.label)

    def dataciteMetadata(self):
        # Returns citation metadata as a DataCite XML record.  (The record
        # includes an encoding declaration, but is not actually encoded.)
        # This method does not check metadata requirements, and always
        # returns a record; missing attributes will be "(:unav)".  The
        # mapping is based on the identifier's preferred metadata profile
        # but with priority given to the DataCite fields.
        import impl.datacite as datacite

        return datacite.formRecord(
            self.identifier, self.cm, supplyMissing=True, profile=self.profile.label
        )

    USER = "U"
    GROUP = "G"
    agentRole = django.db.models.CharField(
        max_length=1, blank=True, choices=[(USER, "user"), (GROUP, "group")], default=""
    )
    # If the identifier is the persistent identifier of an agent, the
    # agent's role; otherwise, empty.

    agentRoleDisplayToCode = {"user": USER, "group": GROUP}

    @property
    def isAgentPid(self):
        return self.agentRole != ""

    isTest = django.db.models.BooleanField(editable=False, blank=True)

    # Computed value: True if the identifier is a test identifier.

    def my_full_clean(self, exclude=None, validate_unique=False):
        # This method differs from the Django-supplied full_clean method
        # in two ways: it stops if any field-level validations fail; and
        # the default value for the validate_unique argument is False.
        if exclude is None:
            exclude = []
        else:
            exclude = list(exclude)
        try:
            self.clean_fields(exclude=exclude)
            self.clean()
            if validate_unique:
                self.validate_unique(exclude=exclude)
        except django.core.exceptions.ValidationError as e:
            raise django.core.exceptions.ValidationError(
                f'Error="{repr(e)}" '
                f'Metadata: {pprint.pformat(getattr(self, "cm", "cm=None"))}'
            )

    def clean(self):
        self.baseClean()
        if self.isAgentPid:
            self.cleanAgentPid()
        self.cleanCitationMetadataFields()
        self.checkMetadataRequirements()
        self.computeComputedValues()

    # noinspection PyUnresolvedReferences
    def baseClean(self):
        # noinspection PyUnresolvedReferences
        if self.owner is not None and self.ownergroup is None:
            self.ownergroup = self.owner.group
        else:
            if (self.owner is not None) ^ (self.ownergroup is not None):
                e = "Owner/ownergroup inconsistency."
                raise django.core.exceptions.ValidationError(
                    {"owner": e, "ownergroup": e}
                )
            if self.ownergroup is not None:
                # noinspection PyUnresolvedReferences
                if self.ownergroup != self.owner.group:
                    raise django.core.exceptions.ValidationError(
                        {
                            "ownergroup": "Identifier's ownergroup does not match "
                            + "identifier's owner's group."
                        }
                    )
        t = int(time.time())
        if self.createTime == "":
            self.createTime = t
        if self.updateTime == "":
            self.updateTime = t
        if self.updateTime < self.createTime:
            raise django.core.exceptions.ValidationError(
                {"updateTime": "Update time precedes creation time."}
            )
        self.unavailableReason = self.unavailableReason.strip()
        if self.unavailableReason != "" and not self.isUnavailable:
            raise django.core.exceptions.ValidationError(
                {
                    "unavailableReason": "Non-unavailable identifier has nonempty "
                    + "unavailability reason."
                }
            )
        self.crossrefMessage = self.crossrefMessage.strip()
        if self.isDoi:
            if self.isDatacite:
                # noinspection PyUnresolvedReferences
                if self.datacenter is None:
                    raise django.core.exceptions.ValidationError(
                        {"datacenter": "Missing datacenter."}
                    )
                if self.crossrefMessage != "":
                    raise django.core.exceptions.ValidationError(
                        {
                            "crossrefMessage": "DataCite DOI has nonempty Crossref message."
                        }
                    )
            elif self.isCrossref:
                # noinspection PyUnresolvedReferences
                if self.datacenter is not None:
                    # This is the correct error message in most cases.
                    raise django.core.exceptions.ValidationError(
                        {
                            "_crossref": "Crossref registration is incompatible with shoulder."
                        }
                    )
                try:
                    ezidapp.models.validation.crossrefDoi(self.identifier)
                except django.core.exceptions.ValidationError as e:
                    raise django.core.exceptions.ValidationError({"identifier": e})
                if not self.exported:
                    raise django.core.exceptions.ValidationError(
                        {"exported": "Crossref-registered identifier must be exported."}
                    )
                if self.isReserved ^ (self.crossrefStatus == self.CR_RESERVED):
                    e = "Identifier status/Crossref status inconsistency."
                    raise django.core.exceptions.ValidationError(
                        {"status": e, "crossrefStatus": e}
                    )
                if self.isCrossrefGood and self.crossrefMessage != "":
                    raise django.core.exceptions.ValidationError(
                        {
                            "crossrefMessage": "Non-problematic Crossref-registered "
                            + "DOI has nonempty Crossref message."
                        }
                    )
            else:
                assert False, "unhandled case"
        else:
            # noinspection PyUnresolvedReferences
            if self.datacenter is not None:
                raise django.core.exceptions.ValidationError(
                    {"datacenter": "Non-DOI identifier has datacenter."}
                )
            if self.crossrefStatus != "":
                raise django.core.exceptions.ValidationError(
                    {
                        "crossrefStatus": "Only DOI identifiers may be registered with Crossref."
                    }
                )
            if self.crossrefMessage != "":
                raise django.core.exceptions.ValidationError(
                    {
                        "crossrefMessage": "Non-DOI identifier has nonempty "
                        + "Crossref message."
                    }
                )
        if self.target == "":
            self.target = self.defaultTarget
        if "${identifier}" in self.target:
            # Insert the identifier in the target URL... but for safety,
            # ensure that the resulting URL is still valid.
            self.target = self.target.replace(
                "${identifier}", urllib.parse.quote(self.identifier, ":/")
            )
            self._meta.get_field("target").run_validators(self.target)
        # Per RFC 3986, URI schemes are case-insensitive, but some systems
        # we interact with require the scheme to be lowercase.
        scheme, rest = self.target.split(":", 1)
        self.target = f"{scheme.lower()}:{rest}"
        if self.profile is None:
            self.profile = self.defaultProfile
        for k, v in list(self.cm.items()):
            if k.strip() != k or k == "" or k.startswith("_"):
                raise django.core.exceptions.ValidationError(
                    {"cm": "Invalid citation metadata key."}
                )
            vs = v.strip()
            if vs == "":
                del self.cm[k]
            elif vs != v:
                self.cm[k] = vs

    def cleanAgentPid(self):
        # Checks applicable to agent PIDs only.
        import impl.util2 as util2

        if not self.isArk:
            raise django.core.exceptions.ValidationError(
                {"identifier": "Agent PID is not an ARK."}
            )
        if (
            self.owner is None
            or self.owner.username != django.conf.settings.ADMIN_USERNAME
        ):
            raise django.core.exceptions.ValidationError(
                {"owner": "Agent PID is not owned by the EZID administrator."}
            )
        if not self.isPublic:
            raise django.core.exceptions.ValidationError(
                {"status": "Agent PID is not public."}
            )
        if self.exported:
            raise django.core.exceptions.ValidationError(
                {"exported": "Agent PID is exported."}
            )
        if self.target != self.defaultTarget:
            raise django.core.exceptions.ValidationError(
                {"target": "Agent PID has non-default target URL."}
            )
        # N.B.: the isTest field hasn't been computed yet.
        if util2.isTestIdentifier(self.identifier):
            raise django.core.exceptions.ValidationError(
                {"identifier": "Agent PID is a test identifier."}
            )

    def cleanCitationMetadataFields(self):
        # Cleans certain citation metadata fields on which EZID imposes
        # structure.
        # import ezidapp.management.commands.crossref as crossref
        import impl.datacite as datacite

        if "datacite.resourcetype" in self.cm:
            try:
                self.cm[
                    "datacite.resourcetype"
                ] = ezidapp.models.validation.resourceType(
                    self.cm["datacite.resourcetype"]
                )
            except django.core.exceptions.ValidationError as e:
                raise django.core.exceptions.ValidationError(
                    {"datacite.resourcetype": e}
                )
        if "datacite" in self.cm:
            try:
                # In validating DataCite XML records, we always require that
                # records be well-formed and that they look sufficiently like
                # DataCite records that we can process them.  For reserved
                # identifiers we stop there to allow incomplete records to be
                # submitted; otherwise, we fully validate records against the
                # appropriate XML schema to ensure they will be accepted by
                # DataCite.  (Note that this check is performed for all types
                # of identifiers, not just DOIs.)
                self.cm["datacite"] = datacite.validateDcmsRecord(
                    self.identifier,
                    self.cm["datacite"],
                    schemaValidate=(not self.isReserved),
                )
            except AssertionError as e:
                raise django.core.exceptions.ValidationError(
                    {
                        "datacite": f"Metadata validation error: "
                        f"{impl.util.oneLine(str(e))}. "
                        f'metadata="{self.cm.get("datacite", "<missing>")}"'
                    }
                )
        if "crossref" in self.cm:
            try:
                # Our validation of Crossref XML records is incomplete (the
                # schema is way too complicated).  As with DataCite XML
                # records, we simply require that they be well-formed and that
                # the parts that EZID cares about are present and sufficiently
                # correct to support our processing.
                self.cm["crossref"] = crossref.validateBody(self.cm["crossref"])
                if self.isDoi and not self.isReserved:
                    self.cm["crossref"] = crossref.replaceTbas(
                        self.cm["crossref"], self.identifier[4:], self.resolverTarget
                    )
            except AssertionError as e:
                raise django.core.exceptions.ValidationError(
                    {
                        "crossref": f"Metadata validation error: "
                        f"{impl.util.oneLine(str(e))}."
                    }
                )

    def checkMetadataRequirements(self):
        import impl.datacite as datacite

        if self.isDatacite and not self.isReserved:
            # If the identifier has DataCite or Crossref XML metadata, we
            # know automatically that metadata requirements are satisfied
            # (in the Crossref case, by virtue of the design of the
            # Crossref-to-DataCite transform, which always generates a
            # complete DataCite record).
            if "datacite" not in self.cm and (
                not self.usesCrossrefProfile or "crossref" not in self.cm
            ):
                try:
                    datacite.formRecord(
                        self.identifier, self.cm, profile=self.profile.label
                    )
                except AssertionError as e:
                    raise django.core.exceptions.ValidationError(
                        f"Public DOI metadata requirements not satisfied: {str(e)}."
                    )
        if self.isCrossref and not self.isReserved and "crossref" not in self.cm:
            raise django.core.exceptions.ValidationError(
                f"Registration with Crossref requires Crossref metadata supplied "
                f"as value of element 'crossref'. Received metadata: {self.cm}"
            )

    def computeComputedValues(self):
        import impl.util2 as util2

        self.isTest = util2.isTestIdentifier(self.identifier)

    def __str__(self):
        return self.identifier

    def toLegacy(self):
        # Returns a legacy representation of the identifier.  See the
        # inverse of this method, 'fromLegacy' below.
        d = self.cm.copy()
        d["_o"] = self.owner.pid if self.owner is not None else "anonymous"
        d["_g"] = self.ownergroup.pid if self.ownergroup is not None else "anonymous"
        d["_c"] = str(self.createTime)
        d["_u"] = str(self.updateTime)
        d["_p"] = self.profile.label
        if self.isPublic:
            d["_t"] = self.target
        else:
            if self.isReserved:
                d["_is"] = "reserved"
            else:
                d["_is"] = "unavailable"
                if self.unavailableReason != "":
                    d["_is"] += " | " + self.unavailableReason
            d["_t"] = self.resolverTarget
            d["_t1"] = self.target
        if not self.exported:
            d["_x"] = "no"
        if self.isDatacite:
            # noinspection PyUnresolvedReferences
            d["_d"] = self.datacenter.symbol
        if self.isCrossref:
            d["_cr"] = "yes | " + self.get_crossrefStatus_display()
            if self.crossrefMessage != "":
                d["_cr"] += " | " + self.crossrefMessage
        if self.isAgentPid:
            d["_ezid_role"] = "user" if self.agentRole == self.USER else "group"
        return d

    _legacyUnavailableStatusRE = re.compile("unavailable \| (.*)")

    def fromLegacy(self, d):
        # Creates an identifier from a legacy representation (or more
        # accurately, fills out an identifier from a legacy
        # representation).  This method should be called after the
        # concrete subclass instance has been created with the identifier
        # set as in, for example, SearchIdentifier(identifier=...).  All
        # foreign key values (owner, ownergroup, datacenter, profile) must
        # be set externally to this method.  Finally,
        # computeComputedValues should be called after this method to fill
        # out the rest of the object.
        self.createTime = int(d["_c"])
        self.updateTime = int(d["_u"])
        if "_is" in d:
            if d["_is"] == "reserved":
                self.status = self.RESERVED
            else:
                self.status = self.UNAVAILABLE
                m = self._legacyUnavailableStatusRE.match(d["_is"])
                if m:
                    self.unavailableReason = m.group(1)
            self.target = d["_t1"]
        else:
            self.status = self.PUBLIC
            self.target = d["_t"]
        self.exported = "_x" not in d
        for k, v in list(d.items()):
            if not k.startswith("_"):
                self.cm[k] = v
        if "_cr" in d:
            statuses = dict(
                (v, k) for k, v in self._meta.get_field("crossrefStatus").get_choices()
            )
            assert d["_cr"].startswith("yes | "), "malformed legacy Crossref status"
            l = [s for s in list(statuses.keys()) if d["_cr"][6:].startswith(s)]
            assert len(l) == 1, "unrecognized legacy Crossref status"
            self.crossrefStatus = statuses[l[0]]
            if len(d["_cr"]) > 6 + len(l[0]):
                m = d["_cr"][6 + len(l[0]) :]
                assert m.startswith(" | "), "malformed legacy Crossref status"
                self.crossrefMessage = m[3:]
        if "_ezid_role" in d:
            self.agentRole = self.USER if d["_ezid_role"] == "user" else self.GROUP




class Search(django.db.models.Lookup):
    lookup_name = 'search'

    def as_mysql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return 'MATCH (%s) AGAINST (%s IN BOOLEAN MODE)' % (lhs, rhs), params


django.db.models.CharField.register_lookup(Search)
django.db.models.TextField.register_lookup(Search)


class SearchIdentifier(Identifier):
    # An identifier as stored in the search database.

    # Foreign key declarations.  Note that in the search database every
    # identifier has an owner; anonymous identifiers are not stored.
    # For performance we do not validate foreign key references (but of
    # course they're still checked in the database).

    # non_validating_key = django.apps.apps.get_model('ezidapp', '')
    owner = ezidapp.models.custom_fields.NonValidatingForeignKey(
        'ezidapp.SearchUser',
        on_delete=django.db.models.PROTECT,
    )
    ownergroup = ezidapp.models.custom_fields.NonValidatingForeignKey(
        'ezidapp.SearchGroup',
        blank=True,
        null=True,
        default=None,
        on_delete=django.db.models.PROTECT,
    )
    datacenter = ezidapp.models.custom_fields.NonValidatingForeignKey(
        'ezidapp.SearchDatacenter',
        blank=True,
        null=True,
        default=None,
        on_delete=django.db.models.PROTECT,
    )

    import ezidapp.models.profile

    profile = ezidapp.models.custom_fields.NonValidatingForeignKey(
        ezidapp.models.profile.SearchProfile,
        # 'ezidapp.SearchProfile',
        blank=True,
        null=True,
        default=None,
        on_delete=django.db.models.PROTECT,
    )

    @property
    def defaultProfile(self):
        return ezidapp.models.search_profile.SearchProfile, "label", label
        #     )
        #     return p

        return _getProfile(impl.util2.defaultProfile(self.identifier))

    searchableTarget = django.db.models.CharField(max_length=255, editable=False)
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
        blank=True, null=True, editable=False
    )
    # The year portion of resourcePublicationDate, as a numeric, if one
    # could be extracted; otherwise, None.

    resourceType = django.db.models.TextField(editable=False)
    # Computed value: the resource's type, if available, as mapped from
    # the identifier's preferred metadata profile; otherwise, empty.

    searchableResourceType = django.db.models.CharField(
        max_length=2,
        editable=False,
        choices=sorted(
            [(v, k) for k, v in list(ezidapp.models.validation.resourceTypes.items())],
            key=lambda x: x[1],
            # cmp=lambda a, b: cmp(a[1], b[1]),
        ),
    )
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
        max_length=indexedPrefixLength, editable=False
    )
    resourceTitlePrefix = django.db.models.CharField(
        max_length=indexedPrefixLength, editable=False
    )
    resourcePublisherPrefix = django.db.models.CharField(
        max_length=indexedPrefixLength, editable=False
    )

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

    linkIsBroken = django.db.models.BooleanField(editable=False, default=False)
    # Computed value: True if the target URL is broken.  This field is
    # set only by the link checker update daemon.
    # N.B.: see note under updateFromLegacy below regarding this field.

    hasIssues = django.db.models.BooleanField(editable=False)

    # Computed value: True if the identifier "has issues," i.e., has
    # problems of some kind.

    def issueReasons(self):
        # Returns a list of the identifier's issues.
        reasons = []
        if not self.hasMetadata:
            reasons.append("missing metadata")
        if self.linkIsBroken:
            reasons.append("broken link")
        if self.isCrossrefBad:
            reasons.append(
                "Crossref registration "
                + ("warning" if self.crossrefStatus == self.CR_WARNING else "failure")
            )
        return reasons

    def computeHasIssues(self):
        self.hasIssues = not self.hasMetadata or self.linkIsBroken or self.isCrossrefBad

    def computeComputedValues(self):
        super(SearchIdentifier, self).computeComputedValues()
        self.searchableTarget = self.target[::-1][
            : self._meta.get_field("searchableTarget").max_length
        ]
        self.resourceCreator = ""
        self.resourceTitle = ""
        self.resourcePublisher = ""
        self.resourcePublicationDate = ""
        self.resourceType = ""
        km = self.kernelMetadata()
        if km.creator is not None:
            self.resourceCreator = km.creator
        if km.title is not None:
            self.resourceTitle = km.title
        if km.publisher is not None:
            self.resourcePublisher = km.publisher
        if km.date is not None:
            self.resourcePublicationDate = km.date
        d = km.validatedDate
        if d is not None:
            self.searchablePublicationYear = int(d[:4])
        else:
            self.searchablePublicationYear = None
        if km.type is not None:
            self.resourceType = km.type
        t = km.validatedType
        if t is not None:
            self.searchableResourceType = ezidapp.models.validation.resourceTypes[
                t.split("/")[0]
            ]
        else:
            self.searchableResourceType = ""
        kw = [self.identifier, self.owner.username, self.ownergroup.groupname]
        if self.isDatacite:
            kw.append(self.datacenter.symbol)
        if self.target != self.defaultTarget:
            kw.append(self.target)
        for k, v in list(self.cm.items()):
            if k in ["datacite", "crossref"]:
                try:
                    kw.append(impl.util.extractXmlContent(v))
                except Exception:
                    kw.append(v)
            else:
                kw.append(v)
        self.keywords = " ; ".join(kw)
        self.resourceCreatorPrefix = self.resourceCreator[: self.indexedPrefixLength]
        self.resourceTitlePrefix = self.resourceTitle[: self.indexedPrefixLength]
        self.resourcePublisherPrefix = self.resourcePublisher[
            : self.indexedPrefixLength
        ]
        self.hasMetadata = (
            self.resourceTitle != ""
            and self.resourcePublicationDate != ""
            and (self.resourceCreator != "" or self.resourcePublisher != "")
        )
        self.publicSearchVisible = self.isPublic and self.exported and not self.isTest
        self.oaiVisible = (
            self.publicSearchVisible
            and self.hasMetadata
            and self.target != self.defaultTarget
        )
        self.computeHasIssues()

    def fromLegacy(self, d):
        # See Identifier.fromLegacy.  N.B.: computeComputedValues should
        # be called after this method to fill out the rest of the object.
        super(SearchIdentifier, self).fromLegacy(d)
        self.owner = _getUser(d["_o"])
        self.ownergroup = _getGroup(d["_g"])
        self.profile = _getProfile(d["_p"])
        if self.isDatacite:
            self.datacenter = _getDatacenter(d["_d"])

    # Note that MySQL FULLTEXT indexes must be created outside Django;
    # see .../etc/search-mysql-addendum.sql.

    class Meta(Identifier.Meta):
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
            ("oaiVisible", "updateTime"),
        ]


# The following caches are only added to or replaced entirely;
# existing entries are never modified.  Thus, with appropriate coding
# below, they are threadsafe without needing locking.

# _userCache = None
# _groupCache = None
# _datacenterCache = None
# _profileCache = None


# def clearUserCache():
#     global _userCache
#     _userCache = None
#
#
# def clearGroupCache():
#     global _groupCache
#     _groupCache = None
#
#
# def clearCaches():
#     global _userCache, _groupCache, _datacenterCache, _profileCache
#     _userCache = None
#     _groupCache = None
#     _datacenterCache = None
#     _profileCache = None


# def _getFromCache(cache, model, attribute, key, insertOnMissing=True):
#     # Generic caching function supporting the caches in this module.
#     # Returns (I, cache) where I is the instance of 'model' for which
#     # I.'attribute' = 'key'.  'cache' may be None on input, and it is
#     # possibly set and/or augmented on return.
#     if cache is None:
#         cache = dict((getattr(i, attribute), i) for i in model.objects.all())
#     if key in cache:
#         i = cache[key]
#     else:
#         if insertOnMissing:
#             try:
#                 i = model(**{attribute: key})
#                 i.full_clean(validate_unique=False)
#                 i.save()
#             except django.db.utils.IntegrityError:
#                 # Somebody beat us to it.
#                 i = model.objects.get(**{attribute: key})
#         else:
#             try:
#                 i = model.objects.get(**{attribute: key})
#             except model.DoesNotExist:
#                 raise model.DoesNotExist(
#                     f"No {model.__name__} for {attribute}='{key}'."
#                 )
#         cache[key] = i
#     return i, cache


# def _getUser(pid):
#     global _userCache
#     u, _userCache = _getFromCache(
#         _userCache,
#         ezidapp.models.user.SearchUser,
#         "pid",
#         pid,
#         insertOnMissing=False,
#     )
#     return u


# def _getGroup(pid):
#     global _groupCache
#     g, _groupCache = _getFromCache(
#         _groupCache,
#         ezidapp.models.group.SearchGroup,
#         "pid",
#         pid,
#         insertOnMissing=False,
#     )
#     return g


# def _getDatacenter(symbol):
#     global _datacenterCache
#     d, _datacenterCache = _getFromCache(
#         _datacenterCache,
#         ezidapp.models.datacenter.SearchDatacenter,
#         "symbol",
#         symbol,
#     )
#     return d


def updateFromLegacy(identifier, metadata, forceInsert=False, forceUpdate=False):
    # Inserts or updates an identifier in the search database.  The
    # identifier is constructed from a legacy representation.
    i = SearchIdentifier(identifier=identifier)
    i.fromLegacy(metadata)
    i.my_full_clean()
    # Because SearchDbDaemon's call to this function is really the only
    # place identifiers get inserted and updated in the search database,
    # we're not concerned with race conditions.
    if not forceInsert:
        j = SearchIdentifier.objects.filter(identifier=identifier).only("id")
        if len(j) > 0:
            i.id = j[0].id
    # Ideally we would like to specify that all fields be updated
    # *except* linkIsBroken, but Django does not provide a way to do
    # this.  As a consequence, linkIsBroken's default value will
    # override the previous value in the table.  The next time the link
    # checker update daemon runs it will correct the value, which is
    # some consolation.
    i.save(force_insert=forceInsert, force_update=forceUpdate)


# =============================================================================
#
# EZID :: ezidapp/models.identifier.py
#
# Database model for identifiers in the store database.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2017, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------
import django.apps
import ezidapp.models.util
import impl.util
import django.core.exceptions
import django.db.models
import re

import impl.util2

import ezidapp.models.custom_fields

# import ezidapp.models.identifier
# import ezidapp.models.shoulder
# import ezidapp.models.datacenter
# import ezidapp.models.group
# import ezidapp.models.store_profile
# import ezidapp.models.user
import ezidapp.models.group


def getIdentifier(identifier, prefixMatch=False):
    if prefixMatch:
        l = list(
            StoreIdentifier.objects.select_related(
                "owner", "owner__group", "ownergroup", "datacenter", "profile"
            ).filter(identifier__in=impl.util.explodePrefixes(identifier))
        )
        if len(l) > 0:
            return max(l, key=lambda si: len(si.identifier))
        else:
            raise StoreIdentifier.DoesNotExist()
    else:
        return StoreIdentifier.objects.select_related(
            "owner", "owner__group", "ownergroup", "datacenter", "profile"
        ).get(identifier=identifier)


class StoreIdentifier(Identifier):
    # An identifier as stored in the store database.

    # Foreign key declarations.  For performance we do not validate
    # foreign key references (but of course they're still checked in the
    # database).

    owner = ezidapp.models.custom_fields.NonValidatingForeignKey(
        'ezidapp.StoreUser',
        blank=True,
        null=True,
        on_delete=django.db.models.PROTECT,
    )
    ownergroup = ezidapp.models.custom_fields.NonValidatingForeignKey(
        'ezidapp.StoreGroup',
        blank=True,
        null=True,
        default=None,
        on_delete=django.db.models.PROTECT,
    )
    datacenter = ezidapp.models.custom_fields.NonValidatingForeignKey(
        'ezidapp.StoreDatacenter',
        blank=True,
        null=True,
        default=None,
        on_delete=django.db.models.PROTECT,
    )
    profile = ezidapp.models.custom_fields.NonValidatingForeignKey(
        'ezidapp.StoreProfile',
        blank=True,
        null=True,
        default=None,
        on_delete=django.db.models.PROTECT,
    )

    @property
    def defaultProfile(self):
        return ezidapp.models.util.getProfileByLabel(
            impl.util2.defaultProfile(self.identifier)
        )

    def fromLegacy(self, d):
        # See Identifier.fromLegacy.  N.B.: computeComputedValues should
        # be called after this method to fill out the rest of the object.
        super(StoreIdentifier, self).fromLegacy(d)
        if d["_o"] != "anonymous":
            self.owner = ezidapp.models.util.getUserByPid(d["_o"])
        if d["_g"] != "anonymous":
            self.ownergroup = ezidapp.models.group.getGroupByPid(d["_g"])
        self.profile = ezidapp.models.util.getProfileByLabel(d["_p"])
        if self.isDatacite:
            self.datacenter = ezidapp.models.util.getDatacenterBySymbol(d["_d"])

    def updateFromUntrustedLegacy(self, d, allowRestrictedSettings=False):
        # Fills out a new identifier or (partially) updates an existing
        # identifier from client-supplied (i.e., untrusted) legacy
        # metadata.  When filling out a new identifier the identifier
        # string and owner must already be set as in, for example,
        # StoreIdentifier(identifier=..., owner=...) (but note that the
        # owner may be None to signify an anonymously-owned identifier).
        # If 'allowRestrictedSettings' is True, fields and values that are
        # not ordinarily settable by clients may be set.  Throws
        # django.core.exceptions.ValidationError on all errors.
        # my_full_clean should be called after this method to fully fill
        # out and validate the object.  This method checks for state
        # transition violations and DOI registration agency changes, but
        # does no permissions checking, and in particular, does not check
        # the allowability of ownership changes.
        for k in d:
            if k == "_owner":
                o = ezidapp.models.util.getUserByUsername(d[k])
                anon_user_model = django.apps.apps.get_model('ezidapp', 'AnonymousUser')
                if o is None or o == anon_user_model:
                    raise django.core.exceptions.ValidationError(
                        {"owner": "No such user."}
                    )
                self.owner = o
                self.ownergroup = None
            elif k == "_ownergroup":
                if not allowRestrictedSettings:
                    raise django.core.exceptions.ValidationError(
                        {"ownergroup": "Field is not settable."}
                    )
                g = ezidapp.models.group.getGroupByGroupname(d[k])
                if g is None or g == ezidapp.models.group.AnonymousGroup:
                    raise django.core.exceptions.ValidationError(
                        {"ownergoup": "No such group."}
                    )
                self.ownergroup = g
            elif k == "_created":
                if not allowRestrictedSettings:
                    raise django.core.exceptions.ValidationError(
                        {"createTime": "Field is not settable."}
                    )
                self.createTime = d[k]
            elif k == "_updated":
                if not allowRestrictedSettings:
                    raise django.core.exceptions.ValidationError(
                        {"updateTime": "Field is not settable."}
                    )
                self.updateTime = d[k]
            elif k == "_status":
                if d[k] == "reserved":
                    if self.pk is None or self.isReserved or allowRestrictedSettings:
                        self.status = StoreIdentifier.RESERVED
                        self.unavailableReason = ""
                    else:
                        raise django.core.exceptions.ValidationError(
                            {"status": "Invalid identifier status change."}
                        )
                elif d[k] == "public":
                    self.status = StoreIdentifier.PUBLIC
                    self.unavailableReason = ""
                else:
                    m = re.match("unavailable(?:$| *\|(.*))", d[k])
                    if m:
                        if (
                            self.pk is not None and not self.isReserved
                        ) or allowRestrictedSettings:
                            self.status = StoreIdentifier.UNAVAILABLE
                            if m.group(1) is not None:
                                self.unavailableReason = m.group(1)
                            else:
                                self.unavailableReason = ""
                        else:
                            raise django.core.exceptions.ValidationError(
                                {"status": "Invalid identifier status change."}
                            )
                    else:
                        raise django.core.exceptions.ValidationError(
                            {"status": "Invalid identifier status."}
                        )
            elif k == "_export":
                if d[k].lower() == "yes":
                    self.exported = True
                elif d[k].lower() == "no":
                    self.exported = False
                else:
                    raise django.core.exceptions.ValidationError(
                        {"exported": "Value must be 'yes' or 'no'."}
                    )
            elif k == "_datacenter":
                if not allowRestrictedSettings:
                    raise django.core.exceptions.ValidationError(
                        {"_datacenter": "Field is not settable."}
                    )
                if d[k] != "":
                    datacenter_model = django.apps.apps.get_model(
                        'ezidapp', 'StoreDatacenter'
                    )
                    try:
                        self.datacenter = ezidapp.models.util.getDatacenterBySymbol(
                            d[k]
                        )
                    except datacenter_model.DoesNotExist:
                        raise django.core.exceptions.ValidationError(
                            {"datacenter": "No such datacenter."}
                        )
                else:
                    self.datacenter = None
            elif k == "_crossref":
                if d[k].lower() == "yes":
                    if (
                        self.pk is not None
                        and self.isDatacite
                        and not allowRestrictedSettings
                    ):
                        raise django.core.exceptions.ValidationError(
                            {
                                "crossrefStatus": "DataCite DOI cannot be registered with Crossref."
                            }
                        )
                    if self.isReserved:
                        self.crossrefStatus = StoreIdentifier.CR_RESERVED
                    else:
                        self.crossrefStatus = StoreIdentifier.CR_WORKING
                    self.crossrefMessage = ""
                elif allowRestrictedSettings:
                    if d[k] == "":
                        self.crossrefStatus = ""
                        self.crossrefMessage = ""
                    else:
                        # OK, this is a hack used by the Crossref queue.
                        self.crossrefStatus, self.crossrefMessage = d[k].split("/", 1)
                else:
                    raise django.core.exceptions.ValidationError(
                        {"crossrefStatus": "Value must be 'yes'."}
                    )
            elif k == "_target":
                self.target = d[k]
            elif k == "_profile":
                if d[k] == "":
                    self.profile = None
                else:
                    try:
                        self.profile = ezidapp.models.util.getProfileByLabel(d[k])
                    except django.core.exceptions.ValidationError as e:
                        raise django.core.exceptions.ValidationError({"profile": [e]})
            elif k == "_ezid_role":
                if not allowRestrictedSettings:
                    raise django.core.exceptions.ValidationError(
                        {"_ezid_role": "Field is not settable."}
                    )
                self.agentRole = self.agentRoleDisplayToCode.get(d[k], d[k])
            elif k.startswith("_"):
                raise django.core.exceptions.ValidationError(
                    {k: "Field is not settable."}
                )
            else:
                self.cm[k] = d[k]
