#  Copyright©2022, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Object Relational Mapper (ORM) models for identifiers
"""
import pprint
import re
import time
import urllib.error
import urllib.parse
import urllib.request

import django.apps
import django.conf
import django.core.exceptions
import django.core.serializers.json
import django.core.validators
import django.db
import django.db.models
import django.db.utils

import ezidapp.models.group
import ezidapp.models.profile
import ezidapp.models.user
import ezidapp.models.util
import ezidapp.models.validation
import impl.crossref
import impl.datacite
import impl.mapping
import impl.util
import impl.util2

MAX_SEARCHABLE_TARGET_LENGTH = 255



def getDefaultProfileLabel(identifier):
    """Return the label of the default metadata profile for a given qualified identifier."""
    if identifier.startswith("ark:/"):
        return django.conf.settings.DEFAULT_ARK_PROFILE
    if identifier.startswith("doi:"):
        return django.conf.settings.DEFAULT_DOI_PROFILE
    if identifier.startswith("uuid:"):
        return django.conf.settings.DEFAULT_UUID_PROFILE
    raise AssertionError(f'Not a valid qualified identifier: {identifier}')
    # return ezidapp.models.util.getProfileByLabel(self.identifier)
    # return ezidapp.models.util.getProfileByLabel(defaultProfile(self.identifier))


class IdentifierBase(django.db.models.Model):
    """Minted identifiers and related data

    Almost everything in EZID revolves around this table, in which most data related to minted
    identifiers is stored either directly or is referenced in foreign keys.
    """

    def __str__(self):
        return (
            f'{self.__class__.__name__}('
            f'pk={self.pk}, '
            f'id={self.identifier}, '
            f'isArk={self.isArk}, '
            f'isDOI={self.isDoi}, '
            f'isDataCite={self.isDatacite}, '
            f'isCrossref={self.isCrossref}, '
            f'target={self.target}, '
            f'ownerId={self.owner_id}'
            f')'
        )

    class Meta:
        """This model does not itself cause a table to be created. Tables are created by
        subclasses below.
        """

        abstract = True

    # The identifier in qualified, normalized form, e.g.,
    # "ark:/12345/abc" or "doi:10.1234/ABC".
    identifier = django.db.models.CharField(
        max_length=impl.util.maxIdentifierLength,
        unique=True,
        validators=[ezidapp.models.validation.anyIdentifier],
    )

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

    datacenter = django.db.models.ForeignKey(
        'ezidapp.Datacenter',
        blank=True,
        null=True,
        default=None,
        on_delete=django.db.models.PROTECT,
    )

    profile = django.db.models.ForeignKey(
        'ezidapp.Profile',
        blank=True,
        null=True,
        default=None,
        on_delete=django.db.models.PROTECT,
    )

    def updateFromUntrustedLegacy(self, d, allowRestrictedSettings=False):
        """Fill out a new identifier or (partially) updates an existing
        identifier from client-supplied (i.e., untrusted) legacy
        metadata

        When filling out a new identifier the identifier
        string and owner must already be set as in, for example,
        Identifier(identifier=..., owner=...) (but note that the
        owner may be None to signify an anonymously-owned identifier).
        If 'allowRestrictedSettings' is True, fields and values that are
        not ordinarily settable by clients may be set. Throws
        django.core.exceptions.ValidationError on all errors.
        my_full_clean should be called after this method to fully fill
        out and validate the object. This method checks for state
        transition violations and DOI registration agency changes, but
        does no permissions checking, and in particular, does not check
        if ownership changes are allowed.
        """
        for k in d:
            if k == "_owner":
                o = ezidapp.models.util.getUserByUsername(d[k])
                # anon_user_model = django.apps.apps.get_model('ezidapp', 'AnonymousUser')
                # if o is None or o == anon_user_model:
                if o is None or o == ezidapp.models.user.AnonymousUser:
                    raise django.core.exceptions.ValidationError({"owner": "No such user."})
                self.owner = o
                self.ownergroup = None
            elif k == "_ownergroup":
                if not allowRestrictedSettings:
                    raise django.core.exceptions.ValidationError(
                        {"ownergroup": "Field is not settable."}
                    )
                g = ezidapp.models.util.getGroupByGroupname(d[k])
                if g is None or g == ezidapp.models.group.AnonymousGroup:
                    raise django.core.exceptions.ValidationError({"ownergroup": "No such group."})
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
                        self.status = Identifier.RESERVED
                        self.unavailableReason = ""
                    else:
                        raise django.core.exceptions.ValidationError(
                            {"status": "Invalid identifier status change."}
                        )
                elif d[k] == "public":
                    self.status = Identifier.PUBLIC
                    self.unavailableReason = ""
                else:
                    m = re.match("unavailable(?:$| *\\|(.*))", d[k])
                    if m:
                        if (self.pk is not None and not self.isReserved) or allowRestrictedSettings:
                            self.status = Identifier.UNAVAILABLE
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
                    datacenter_model = django.apps.apps.get_model('ezidapp', 'Datacenter')
                    try:
                        self.datacenter = ezidapp.models.util.getDatacenterBySymbol(d[k])
                    except datacenter_model.DoesNotExist:
                        raise django.core.exceptions.ValidationError(
                            {"datacenter": "No such datacenter."}
                        )
                else:
                    self.datacenter = None
            elif k == "_crossref":
                if d[k].lower() == "yes":
                    if self.pk is not None and self.isDatacite and not allowRestrictedSettings:
                        raise django.core.exceptions.ValidationError(
                            {"crossrefStatus": "DataCite DOI cannot be registered with Crossref."}
                        )
                    if self.isReserved:
                        self.crossrefStatus = Identifier.CR_RESERVED
                    else:
                        self.crossrefStatus = Identifier.CR_WORKING
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
                raise django.core.exceptions.ValidationError({k: "Field is not settable."})
            else:
                self.metadata[k] = d[k]

    owner = django.db.models.ForeignKey(
        'ezidapp.User',
        blank=True,
        null=True,
        default=None,
        on_delete=django.db.models.PROTECT,
    )

    ownergroup = django.db.models.ForeignKey(
        'ezidapp.Group',
        blank=True,
        null=True,
        default=None,
        on_delete=django.db.models.PROTECT,
    )

    # The time the identifier was created as a Unix timestamp. If not
    # specified, the current time is used.
    createTime = django.db.models.IntegerField(
        blank=True,
        default="",
        validators=[django.core.validators.MinValueValidator(0)],
    )

    # The time the identifier was last updated as a Unix timestamp. If
    # not specified, the current time is used.
    updateTime = django.db.models.IntegerField(
        blank=True,
        default="",
        validators=[django.core.validators.MinValueValidator(0)],
        db_index=True,
    )

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

    # If the status is UNAVAILABLE then, optionally, a reason for the
    # unavailability, e.g., "withdrawn"; otherwise, empty.
    unavailableReason = django.db.models.TextField(blank=True, default="")

    # Export control: determines if the identifier is publicized by
    # exporting it to external indexing and harvesting services.
    # Although this flag may be set independently of the status, in fact
    # it has effect only if the status is public.
    # This field is toggled by the index field in demo/advanced
    exported = django.db.models.BooleanField(default=True)

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
    # no datacenter and a nonempty crossrefStatus. Someday, a true
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

    # For the CR_WARNING and CR_FAILURE Crossref statuses only, any
    # message received from Crossref; otherwise, empty.
    crossrefMessage = django.db.models.TextField(blank=True, default="")

    # The identifier's nominal target URL, e.g., "http://foo.com/bar". (The target URL actually
    # registered with resolvers depends on the identifier's status.)
    #
    # EZID supplies a default target URL that incorporates the identifier in it, so this field will
    # in practice never be empty. The length limit of 2000 characters is not arbitrary, but is the
    # de facto limit accepted by most web browsers.
    target = django.db.models.URLField(
        max_length=2000,
        blank=True,
        default="",
        validators=[ezidapp.models.validation.unicodeBmpOnly],
    )

    @property
    def defaultTarget(self):
        return impl.util2.defaultTargetUrl(self.identifier)

    @property
    def resolverTarget(self):
        """The URL the identifier actually resolves to."""
        if self.isReserved:
            return self.defaultTarget
        elif self.isUnavailable:
            return impl.util2.tombstoneTargetUrl(self.identifier)
        else:
            return self.target

    @property
    def defaultProfile(self):
        """The identifier's preferred metadata profile.

        There is currently no constraint on profile labels, or on use of metadata fields corresponding
        to profiles. Note that EZID supplies a default profile that depends on the identifier type,
        so this field will in practice never be None.
        """
        profile_label = getDefaultProfileLabel(self.identifier)
        return ezidapp.models.util.getProfileByLabel(profile_label)

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

    # Note: These properties are unpleasant - they should be defined
    # as enums though the values are stored in the database.
    @property
    def usesSchemaOrgProfile(self):
        return self.profile.label == "schema_org"

    @property
    def usesArkProfile(self):
        return self.profile.label == "ark"

    @property
    def usesEZIDProfile(self):
        return self.profile.label == "ezid"

    @property
    def usesNIHdcProfile(self):
        return self.profile.label == "NIHdc"

    # All of the identifier's citation metadata as a dictionary of
    # name/value pairs, e.g., { "erc.who": "Proust, Marcel", ... }.
    cm = django.db.models.BinaryField(default=dict)

    metadata = django.db.models.JSONField(
        encoder=django.core.serializers.json.DjangoJSONEncoder,
        blank=True,
        # null=True,
        default=dict,
    )

    @property
    def kernelMetadata(self):
        # Returns citation metadata as a mapping.KernelMetadata object.
        # The mapping is based on the identifier's preferred metadata
        # profile. Missing attributes will be None.
        return impl.mapping.map(self.metadata, profile=self.profile.label)

    def dataciteMetadata(self):
        # Returns citation metadata as a DataCite XML record. (The record
        # includes an encoding declaration, but is not actually encoded.)
        # This method does not check metadata requirements, and always
        # returns a record; missing attributes will be "(:unav)". The
        # mapping is based on the identifier's preferred metadata profile
        # but with priority given to the DataCite fields.
        return impl.datacite.formRecord(
            self.identifier, self.metadata, supplyMissing=True, profile=self.profile.label
        )

    # If the identifier is the persistent identifier of an agent, the
    # agent's role; otherwise, empty.
    USER = "U"
    GROUP = "G"
    agentRole = django.db.models.CharField(
        max_length=1,
        blank=True,
        choices=[(USER, "user"), (GROUP, "group")],
        default="",
    )
    agentRoleDisplayToCode = {"user": USER, "group": GROUP}

    @property
    def isAgentPid(self):
        return self.agentRole != ""

    # Computed value: True if the identifier is a test identifier.
    isTest = django.db.models.BooleanField(editable=False, blank=True)

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
                f'Metadata: {pprint.pformat(getattr(self, "metadata", "metadata=None"))}'
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
                raise django.core.exceptions.ValidationError({"owner": e, "ownergroup": e})
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
                        {"crossrefMessage": "DataCite DOI has nonempty Crossref message."}
                    )
            elif self.isCrossref:
                # noinspection PyUnresolvedReferences
                if self.datacenter is not None:
                    # This is the correct error message in most cases.
                    raise django.core.exceptions.ValidationError(
                        {"_crossref": "Crossref registration is incompatible with shoulder."}
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
                    raise django.core.exceptions.ValidationError({"status": e, "crossrefStatus": e})
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
                    {"crossrefStatus": "Only DOI identifiers may be registered with Crossref."}
                )
            if self.crossrefMessage != "":
                raise django.core.exceptions.ValidationError(
                    {"crossrefMessage": "Non-DOI identifier has nonempty " + "Crossref message."}
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
        for k, v in list(self.metadata.items()):
            if k.strip() != k or k == "" or k.startswith("_"):
                raise django.core.exceptions.ValidationError(
                    {"metadata": "Invalid citation metadata key."}
                )
            vs = v.strip()
            if vs == "":
                del self.metadata[k]
            elif vs != v:
                self.metadata[k] = vs

    def cleanAgentPid(self):
        # Checks applicable to agent PIDs only.
        if not self.isArk:
            raise django.core.exceptions.ValidationError({"identifier": "Agent PID is not an ARK."})
        if self.owner is None or self.owner.username != django.conf.settings.ADMIN_USERNAME:
            raise django.core.exceptions.ValidationError(
                {"owner": "Agent PID is not owned by the EZID administrator."}
            )
        if not self.isPublic:
            raise django.core.exceptions.ValidationError({"status": "Agent PID is not public."})
        if self.exported:
            raise django.core.exceptions.ValidationError({"exported": "Agent PID is exported."})
        if self.target != self.defaultTarget:
            raise django.core.exceptions.ValidationError(
                {"target": "Agent PID has non-default target URL."}
            )
        # N.B.: the isTest field hasn't been computed yet.
        if impl.util2.isTestIdentifier(self.identifier):
            raise django.core.exceptions.ValidationError(
                {"identifier": "Agent PID is a test identifier."}
            )

    def cleanCitationMetadataFields(self):
        # Cleans certain citation metadata fields on which EZID imposes
        # structure.
        if "datacite.resourcetype" in self.metadata:
            try:
                self.metadata["datacite.resourcetype"] = ezidapp.models.validation.resourceType(
                    self.metadata["datacite.resourcetype"]
                )
            except django.core.exceptions.ValidationError as e:
                raise django.core.exceptions.ValidationError({"datacite.resourcetype": e})
        if "datacite" in self.metadata:
            try:
                # In validating DataCite XML records, we always require that records be well-formed
                # and that they look sufficiently like DataCite records that we can process them.
                # For reserved identifiers we stop there to allow incomplete records to be
                # submitted; otherwise, we fully validate records against the appropriate XML schema
                # to ensure they will be accepted by DataCite.
                #
                # This check is performed for all types of identifiers, not just DOIs.
                self.metadata["datacite"] = impl.datacite.validateDcmsRecord(
                    self.identifier,
                    self.metadata["datacite"],
                    schemaValidate=(not self.isReserved),
                )
            except AssertionError as e:
                raise django.core.exceptions.ValidationError(
                    {
                        "datacite": f"Metadata validation error: "
                        f"{impl.util.oneLine(str(e))}. "
                        f'metadata="{self.metadata.get("datacite", "<missing>")}"'
                    }
                )
        if "crossref" in self.metadata:
            try:
                # Our validation of Crossref XML records is incomplete (the
                # schema is way too complicated). As with DataCite XML
                # records, we simply require that they be well-formed and that
                # the parts that EZID cares about are present and sufficiently
                # correct to support our processing.
                self.metadata["crossref"] = impl.crossref.validateBody(self.metadata["crossref"])
                if self.isDoi and not self.isReserved:
                    self.metadata["crossref"] = impl.crossref.replaceTbas(
                        self.metadata["crossref"], self.identifier[4:], self.resolverTarget
                    )
            except AssertionError as e:
                raise django.core.exceptions.ValidationError(
                    {"crossref": f"Metadata validation error: " f"{impl.util.oneLine(str(e))}."}
                )

    def checkMetadataRequirements(self):
        if self.isDatacite and not self.isReserved:
            # If the identifier has DataCite or Crossref XML metadata, we
            # know automatically that metadata requirements are satisfied
            # (in the Crossref case, by virtue of the design of the
            # Crossref-to-DataCite transform, which always generates a
            # complete DataCite record).
            if "datacite" not in self.metadata and (
                not self.usesCrossrefProfile or "crossref" not in self.metadata
            ):
                try:
                    impl.datacite.formRecord(
                        self.identifier, self.metadata, profile=self.profile.label
                    )
                except AssertionError as e:
                    raise django.core.exceptions.ValidationError(
                        f"Public DOI metadata requirements not satisfied: {str(e)}."
                    )
        if self.isCrossref and not self.isReserved and "crossref" not in self.metadata:
            raise django.core.exceptions.ValidationError(
                f"Registration with Crossref requires Crossref metadata supplied "
                f"as value of element 'crossref'. Received metadata: {self.metadata}"
            )

    def computeComputedValues(self):
        self.isTest = impl.util2.isTestIdentifier(self.identifier)

    def toLegacy(self):
        """Return a legacy representation of the identifier

        See the inverse of this method 'fromLegacy' below.

        This function is currently used as the first step in preparing metadata for return to API
        client.
        """
        d = self.metadata.copy()
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

    _legacyUnavailableStatusRE = re.compile("unavailable \\| (.*)")

    def fromLegacy(self, d):
        """Create an identifier from a legacy representation (or more
        accurately, fills out an identifier from a legacy
        representation).

        This method should be called after the
        concrete subclass instance has been created with the identifier
        set as in, for example, Identifier(identifier=...). All
        foreign key values (owner, ownergroup, datacenter, profile) must
        be set externally to this method. Finally,
        computeComputedValues should be called after this method to fill
        out the rest of the object.
        """

        if d["_o"] != "anonymous":
            self.owner = ezidapp.models.util.getUserByPid(d["_o"])

        if d["_g"] != "anonymous":
            self.ownergroup = ezidapp.models.util.getGroupByPid(d["_g"])

        self.profile = ezidapp.models.util.getProfileByLabel(d["_p"])

        if self.isDatacite:
            self.datacenter = ezidapp.models.util.getDatacenterBySymbol(d["_d"])

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
                # TODO: Previous .cm. Can the new JSON field be used directly as a dict?
                self.metadata[k] = v

        if "_cr" in d:
            statuses = dict((v, k) for k, v in self._meta.get_field("crossrefStatus").get_choices())
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

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return 'MATCH (%s) AGAINST (%s IN BOOLEAN MODE)' % (lhs, rhs), params


django.db.models.CharField.register_lookup(Search)
django.db.models.TextField.register_lookup(Search)


class SearchIdentifier(IdentifierBase):
    """An identifier as stored in the search table.

    The SearchIdentifier table expands the regular Identifier table with various indexes to enable
    searches.

    In this table, every identifier has an owner; anonymous identifiers are not stored.

    For performance we do not validate foreign key references (but of course they're still checked
    in the database).
    """

    # Note that MySQL FULLTEXT indexes must be created outside Django;
    # see .../etc/search-mysql-addendum.sql.

    class Meta:
        indexes = [
            django.db.models.Index(fields=['createTime']),
            django.db.models.Index(fields=['updateTime']),
            django.db.models.Index(fields=['oaiVisible', 'updateTime']),
            django.db.models.Index(fields=['owner_id', 'createTime']),
            django.db.models.Index(fields=['owner_id', 'crossrefStatus']),
            django.db.models.Index(fields=['owner_id', 'exported']),
            django.db.models.Index(fields=['owner_id', 'hasIssues']),
            django.db.models.Index(fields=['owner_id', 'hasMetadata']),
            django.db.models.Index(fields=['owner_id', 'identifier']),
            django.db.models.Index(fields=['owner_id', 'profile_id']),
            django.db.models.Index(fields=['owner_id', 'resourceCreatorPrefix']),
            django.db.models.Index(fields=['owner_id', 'resourceTitlePrefix']),
            django.db.models.Index(fields=['owner_id', 'searchablePublicationYear']),
            django.db.models.Index(fields=['owner_id', 'searchableResourceType']),
            django.db.models.Index(fields=['owner_id', 'status']),
            django.db.models.Index(fields=['owner_id', 'updateTime']),
            django.db.models.Index(fields=['ownergroup_id', 'createTime']),
            django.db.models.Index(fields=['ownergroup_id', 'crossrefStatus']),
            django.db.models.Index(fields=['ownergroup_id', 'exported']),
            django.db.models.Index(fields=['ownergroup_id', 'hasIssues']),
            django.db.models.Index(fields=['ownergroup_id', 'identifier']),
            django.db.models.Index(fields=['ownergroup_id', 'isTest']),
            django.db.models.Index(fields=['ownergroup_id', 'profile_id']),
            django.db.models.Index(fields=['ownergroup_id', 'resourceTitlePrefix']),
            django.db.models.Index(fields=['ownergroup_id', 'searchablePublicationYear']),
            django.db.models.Index(fields=['ownergroup_id', 'updateTime']),
            django.db.models.Index(fields=['publicSearchVisible', 'createTime']),
            django.db.models.Index(fields=['publicSearchVisible', 'identifier']),
            django.db.models.Index(fields=['publicSearchVisible', 'searchablePublicationYear']),
            django.db.models.Index(fields=['publicSearchVisible', 'searchableResourceType']),
        ]

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

        self.searchableTarget = self.target[::-1][
            : self._meta.get_field("searchableTarget").max_length
        ]
        self.resourceCreator = ""
        self.resourceTitle = ""
        self.resourcePublisher = ""
        self.resourcePublicationDate = ""
        self.resourceType = ""
        km = self.kernelMetadata
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
            self.searchableResourceType = ezidapp.models.validation.resourceTypes[t.split("/")[0]]
        else:
            self.searchableResourceType = ""
        kw = [self.identifier, self.owner.username, self.ownergroup.groupname]
        if self.isDatacite:
            kw.append(self.datacenter.symbol)
        if self.target != self.defaultTarget:
            kw.append(self.target)
        for k, v in list(self.metadata.items()):
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
        self.resourcePublisherPrefix = self.resourcePublisher[: self.indexedPrefixLength]
        self.hasMetadata = (
            self.resourceTitle != ""
            and self.resourcePublicationDate != ""
            and (self.resourceCreator != "" or self.resourcePublisher != "")
        )
        self.publicSearchVisible = self.isPublic and self.exported and not self.isTest
        self.oaiVisible = (
            self.publicSearchVisible and self.hasMetadata and self.target != self.defaultTarget
        )
        self.computeHasIssues()

    # def fromLegacy(self, d):
    #     # See Identifier.fromLegacy. N.B.: computeComputedValues should
    #     # be called after this method to fill out the rest of the object.
    #     super(Identifier, self).fromLegacy(d)
    #     self.owner = _getUser(d["_o"])
    #     self.ownergroup = _getGroup(d["_g"])
    #     self.profile = _getProfile(d["_p"])
    #     if self.isDatacite:
    #         self.datacenter = _getDatacenter(d["_d"])

    # Computed value. To support searching over target URLs (which are
    # too long to be fully indexed), this field is the last 255
    # characters of the target URL in reverse order.
    searchableTarget = django.db.models.CharField(
        max_length=MAX_SEARCHABLE_TARGET_LENGTH,
        editable=False,
    )

    # Citation metadata follows. Which is to say, the following
    # metadata refers to the resource identified by the identifier, not
    # the identifier itself.

    # Computed value: the resource's creator, if available, as mapped
    # from the identifier's preferred metadata profile; otherwise,
    # empty.
    resourceCreator = django.db.models.TextField(editable=False)

    # Computed value: the resource's title, if available, as mapped from
    # the identifier's preferred metadata profile; otherwise, empty.
    resourceTitle = django.db.models.TextField(editable=False)

    # Computed value: the resource's publisher, if available, as mapped
    # from the identifier's preferred metadata profile; otherwise,
    # empty.
    resourcePublisher = django.db.models.TextField(editable=False)

    # Computed value: the resource's publication date, if available, as
    # mapped from the identifier's preferred metadata profile;
    # otherwise, empty.
    resourcePublicationDate = django.db.models.TextField(editable=False)

    # The year portion of resourcePublicationDate, as a numeric, if one
    # could be extracted; otherwise, None.
    searchablePublicationYear = django.db.models.IntegerField(
        blank=True,
        null=True,
        editable=False,
    )

    # Computed value: the resource's type, if available, as mapped from
    # the identifier's preferred metadata profile; otherwise, empty.
    resourceType = django.db.models.TextField(
        editable=False,
    )

    # The general resource type stored as a single-character mnemonic
    # code, if one could be extracted from resourceType; otherwise,
    # empty.
    searchableResourceType = django.db.models.CharField(
        max_length=2,
        editable=False,
        choices=sorted(
            [(v, k) for k, v in list(ezidapp.models.validation.resourceTypes.items())],
            key=lambda x: x[1],
            # cmp=lambda a, b: cmp(a[1], b[1]),
        ),
    )

    # Computed value: a compendium of all searchable text.
    keywords = django.db.models.TextField(editable=False)

    # To support (partial) ordering by resource creator/title/publisher, which have unbounded length
    # and are therefore cannot be indexed, we add the following fields that hold prefixes of the
    # corresponding fields above.

    indexedPrefixLength = 50
    resourceCreatorPrefix = django.db.models.CharField(
        max_length=indexedPrefixLength,
        editable=False,
    )
    resourceTitlePrefix = django.db.models.CharField(
        max_length=indexedPrefixLength,
        editable=False,
    )
    resourcePublisherPrefix = django.db.models.CharField(
        max_length=indexedPrefixLength,
        editable=False,
    )

    # Computed value: True if resourceTitle and resourcePublicationDate
    # are nonempty, and at least one of resourceCreator and
    # resourcePublisher is nonempty (i.e., the identifier has at least
    # who/what/when metadata in ERC parlance).
    hasMetadata = django.db.models.BooleanField(editable=False)

    # Computed value: True if the identifier is visible in EZID's public
    # search interface, i.e., if the identifier is public and exported
    # and not a test identifier.
    publicSearchVisible = django.db.models.BooleanField(editable=False)

    # Computed value: True if the identifier is visible in the OAI feed,
    # i.e., if the identifier is public and exported and not a test
    # identifier (i.e., if publicSearchVisible is True), and if
    # hasMetadata is True and if the target URL is not the default
    # target URL.
    oaiVisible = django.db.models.BooleanField(editable=False)

    # Computed value: True if the target URL is broken. This field is
    # set only by the link checker update daemon.
    # N.B.: see note under updateFromLegacy below regarding this field.
    linkIsBroken = django.db.models.BooleanField(editable=False, default=False)

    # Computed value: True if the identifier "has issues," i.e., has
    # problems of some kind.
    hasIssues = django.db.models.BooleanField(editable=False)


# def _getFromCache(cache, model, attribute, key, insertOnMissing=True):
#     # Generic caching function supporting the caches in this module.
#     # Returns (I, cache) where I is the instance of 'model' for which
#     # I.'attribute' = 'key'. 'cache' may be None on input, and it is
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


class Identifier(IdentifierBase):

    class Meta:
        indexes = [
            django.db.models.Index(fields=['createTime']),
            django.db.models.Index(fields=['updateTime']),
        ]


class RefIdentifier(IdentifierBase):
    """Identifier referenced in task queues

    The queues hold create, update and/or delete operations that have been scheduled but
    not yet completed.

    TODO: Factor in docstring from IdentifierObjectField:

    - The Identifier model instance primary key (pk) attribute may be set or unset. If
    `pk` is unset, the object is designated as newly created and unsaved (existing only
    in memory). The object does not reference any existing rows in the Identifier table,
    and the identifier in the model instance may or may not exist in the Identifier, or
    other tables.

    - If set, `pk` must reference an existing row in the Identifier table. The
    identifier in the referenced row should be an exact match for identifier in the
    model instance. Other values may differ, representing the identifier in a different
    state.

    - Model instances are normally in an unsaved state only briefly after they're
    created, which is while they are being populated with field values. Once populated,
    the object's `.save()` method is called, which causes the object to be serialized
    and written to a new database row, and the object's `pk` to be set to the index of
    the new row, which enables future model modifications to be synced to the database.

    - If there are issues finding the field values for an object, e.g., if the object
    was intended to hold the results of an operation, and the operation was cancelled or
    interrupted, the object may end up being discarded instead of saved. Any object that
    becomes unreachable without having had its `.save()` method called, is discarded.

    - Calling `.save()` on an object always causes a new row to be inserted if `pk` is
    unset, and an existing row to be updated if `pk` is set. If the inserted or updated
    row breaks any constraints, the operation fails with an IntegrityError or other
    exception.

    - `pk` can be manipulated programmatically before calling `.save()` in order to
    change an update to an insert and vice versa, or to change which row is updated.

    - Sample Identifier model instance, after serialization to JSON. .cm is a nested
    serialized instance of a metadata object."""

    # The identifier in qualified, normalized form, e.g.,
    # "ark:/12345/abc" or "doi:10.1234/ABC".

    # In RefIdentifier, the identifier is not a unique field.
    identifier = django.db.models.CharField(
        max_length=impl.util.maxIdentifierLength,
        validators=[ezidapp.models.validation.anyIdentifier],
        # default='',
        # null=True,
    )


def resolveIdentifier(identifier:str)->Identifier:
    """Returns the target for the specified identifier.

    Separate from getIdentifier below for slight performance boost by avoiding joins.

    Prefix matching is always applied to support suffix pass through.
    """
    #TODO: resolve-300: This method is only used in diag-identifier
    _l = list(
        Identifier.objects.filter(
            identifier__in=impl.util.explodePrefixes(identifier)
        )
    )
    if len(_l) > 0:
        return max(_l, key=lambda si: len(si.identifier))
    raise Identifier.DoesNotExist()


def getIdentifier(identifier:str, prefixMatch:bool=False)->Identifier:
    """Returns Identifier with related entities.
    """
    if prefixMatch:
        l = list(
            Identifier.objects.select_related(
                "owner", "owner__group", "ownergroup", "datacenter", "profile"
            ).filter(identifier__in=impl.util.explodePrefixes(identifier))
        )
        if len(l) > 0:
            return max(l, key=lambda si: len(si.identifier))
        else:
            raise Identifier.DoesNotExist()
    else:
        # TODO: Combine with the select_related above and apply filter in separate step
        # if prefixmatch.
        return Identifier.objects.select_related(
            "owner", "owner__group", "ownergroup", "datacenter", "profile"
        ).get(identifier=identifier)

