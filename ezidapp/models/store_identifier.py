# =============================================================================
#
# EZID :: ezidapp/models/store_identifier.py
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

import impl.util
import django.core.exceptions
import django.db.models
import re

import ezidapp.models.custom_fields
import ezidapp.models.identifier
import impl.util2
import ezidapp.models.shoulder
import ezidapp.models.store_datacenter
import ezidapp.models.store_group
import ezidapp.models.store_profile
import ezidapp.models.store_user


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


class StoreIdentifier(ezidapp.models.identifier.Identifier):
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
        return ezidapp.models.store_profile.getProfileByLabel(
            impl.util2.defaultProfile(self.identifier)
        )

    def fromLegacy(self, d):
        # See Identifier.fromLegacy.  N.B.: computeComputedValues should
        # be called after this method to fill out the rest of the object.
        super(StoreIdentifier, self).fromLegacy(d)
        if d["_o"] != "anonymous":
            self.owner = ezidapp.models.store_user.getUserByPid(d["_o"])
        if d["_g"] != "anonymous":
            self.ownergroup = ezidapp.models.store_group.getGroupByPid(d["_g"])
        self.profile = ezidapp.models.store_profile.getProfileByLabel(d["_p"])
        if self.isDatacite:
            self.datacenter = ezidapp.models.shoulder.getDatacenterBySymbol(d["_d"])

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
                o = ezidapp.models.store_user.getUserByUsername(d[k])
                if o is None or o == ezidapp.models.store_user.AnonymousUser:
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
                g = ezidapp.models.store_group.getGroupByGroupname(d[k])
                if g is None or g == ezidapp.models.store_group.AnonymousGroup:
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
                    try:
                        self.datacenter = ezidapp.models.shoulder.getDatacenterBySymbol(
                            d[k]
                        )
                    except ezidapp.models.store_datacenter.StoreDatacenter.DoesNotExist:
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
                        self.profile = ezidapp.models.store_profile.getProfileByLabel(
                            d[k]
                        )
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
