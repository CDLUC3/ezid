# =============================================================================
#
# EZID :: ezidapp/models/shoulder.py
#
# Database model for shoulders in the store database.
#
# Upon first request this module syncs shoulders and datacenters in
# the store database against counterparts defined in an external
# shoulder file, adding, modifying, and deleting as necessary.
# Shoulders and datacenters are also loaded into in-memory caches.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2016, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------
import logging

import django.apps
import django.conf
import django.core.exceptions
import django.db
import django.db.models
import django.db.transaction

# import ezidapp.models.datacenter
import ezidapp.models.validation
import impl.util
import impl.util2

# import logging

logger = logging.getLogger(__name__)

# acquire = threading.Lock()

# _shoulders = dict(
#     (s.prefix, s)
#     for s in Shoulder.objects.select_related("datacenter").all()
#     if s.active and s.manager == 'ezid'
# )

# dc = dict(
#     (d.symbol, d) for d in ezidapp.models.datacenter.StoreDatacenter.objects.all()
# )
# _datacenters = (dc, dict((d.id, d) for d in list(dc.values())))


# logger = logging.getLogger(__name__)


class ShoulderType(django.db.models.Model):
    shoulder_type = django.db.models.CharField(max_length=32, editable=False)


class RegistrationAgency(django.db.models.Model):
    registration_agency = django.db.models.CharField(max_length=32, editable=False)


class Shoulder(django.db.models.Model):
    # Describes a "shoulder," or identifier namespace.  As a namespace,
    # one shoulder may be a subset of (or contained within) another; in
    # contexts where multiple shoulders apply, the longest (i.e., most
    # precise) match is used.  In practice shoulders have owners (which
    # can be inferenced from their names), but there is no formal notion
    # of ownership.  Shoulders play a limited role within EZID: they're
    # used only as an access mechanism (governing who can create which
    # identifiers) and to provide creation-time configuration defaults.
    # But once created, an identifier stands alone; it has no
    # relationship to any shoulder.

    prefix = django.db.models.CharField(
        max_length=impl.util.maxIdentifierLength,
        unique=True,
        validators=[ezidapp.models.validation.shoulder],
    )
    # The shoulder itself, qualified and normalized, e.g., "ark:/12345/"
    # or "doi:10.1234/FOO".

    type = django.db.models.CharField(max_length=32, editable=False)

    # Computed value: the shoulder's identifier type, e.g., "ARK".  Used
    # only to implement the uniqueness constraint below.

    @property
    def isArk(self):
        return self.type == "ARK"

    @property
    def isDoi(self):
        return self.type == "DOI"

    @property
    def isUuid(self):
        return self.type == "UUID"

    name = django.db.models.CharField(
        max_length=255, validators=[ezidapp.models.validation.nonEmpty]
    )
    # The shoulder's name, e.g., "Brown University Library".

    minter = django.db.models.URLField(max_length=255, blank=True)
    # The absolute URL of the associated minter, or empty if none.

    datacenter = django.db.models.ForeignKey(
        'ezidapp.StoreDatacenter',
        blank=True,
        null=True,
        default=None,
        on_delete=django.db.models.PROTECT,
    )
    # For DataCite DOI shoulders only, the shoulder's default
    # datacenter; otherwise, None.

    crossrefEnabled = django.db.models.BooleanField("Crossref enabled", default=False)

    @property
    def isCrossref(self):
        return self.isDoi and self.crossrefEnabled

    @property
    def isDatacite(self):
        return self.isDoi and not self.crossrefEnabled

    # Computed value.  True if the shoulder is a test shoulder.
    isTest = django.db.models.BooleanField(editable=False)

    # Fields previously only in master_shoulders.txt
    shoulder_type = django.db.models.ForeignKey(
        ShoulderType, on_delete=django.db.models.PROTECT, null=True
    )
    registration_agency = django.db.models.ForeignKey(
        RegistrationAgency, on_delete=django.db.models.PROTECT, null=True
    )
    prefix_shares_datacenter = django.db.models.BooleanField(
        default=False, editable=False
    )
    manager = django.db.models.CharField(
        max_length=32, null=True, blank=True, editable=False
    )
    active = django.db.models.BooleanField(default=False, editable=False)
    redirect = django.db.models.URLField(
        max_length=255, null=True, blank=True, editable=False
    )
    date = django.db.models.DateField(null=True, blank=True, editable=False)
    isSupershoulder = django.db.models.BooleanField(default=False, editable=False)

    class Meta:
        unique_together = ("name", "type")

    def clean(self):
        self.type = self.prefix.split(":")[0].upper()
        self.name = self.name.strip()
        if self.isDoi:
            if self.crossrefEnabled:
                if self.datacenter is not None:
                    raise django.core.exceptions.ValidationError(
                        {"datacenter": "Non-DataCite DOI shoulder has datacenter."}
                    )
            else:
                if self.datacenter is None:
                    raise django.core.exceptions.ValidationError(
                        {"datacenter": "Missing datacenter."}
                    )
        else:
            if self.datacenter is not None:
                raise django.core.exceptions.ValidationError(
                    {"datacenter": "Non-DOI shoulder has datacenter."}
                )
            if self.crossrefEnabled:
                raise django.core.exceptions.ValidationError(
                    {"crossrefEnabled": "Only DOI shoulders may be Crossref enabled."}
                )
        self.isTest = impl.util2.isTestIdentifier(self.prefix)


def getAllShoulders():
    # Returns all shoulders as a list.
    # noinspection PyUnresolvedReferences
    # return list( _shoulders.values())
    return [
        s
        for s in Shoulder.objects.select_related("datacenter").all()
        if s.active and s.manager == 'ezid'
    ]


def getLongestShoulderMatch(identifier):
    lm = None

    for s in (
        Shoulder.objects.annotate(
            identifier=django.db.models.Value(
                identifier, output_field=django.db.models.CharField()
            )
        )
        .select_related("datacenter")
        .filter(identifier__startswith=django.db.models.F('prefix'))
    ):
        # for s in Shoulder.objects.select_related("datacenter").filter(
        #     identifier__startswith='prefix',
        # ):
        if lm is None or len(s.prefix) > len(lm.prefix):
            lm = s

    return lm

    # lm = None
    # # noinspection PyUnresolvedReferences
    # for s in list(_shoulders.values()):
    #     if identifier.startswith(s.prefix):
    #         if lm is None or len(s.prefix) > len(lm.prefix):
    #             lm = s
    # return lm


def getExactShoulderMatch(prefix):
    # Returns the shoulder having prefix 'prefix', or None.
    # noinspection PyUnresolvedReferences
    shoulder_model = Shoulder.objects.select_related("datacenter").get(prefix=prefix)
    # shoulder_model = _shoulders.get(prefix, None)
    # if not shoulder_model:
    # noinspection PyTypeChecker
    # logger.debug('Shoulder lookup from cache failed. prefix="{}"'.format(prefix))
    return shoulder_model


def getArkTestShoulder():
    return _getShoulder(django.conf.settings.SHOULDERS_ARK_TEST)


def getDoiTestShoulder():
    return _getShoulder(django.conf.settings.SHOULDERS_DOI_TEST)


def getCrossrefTestShoulder():
    return _getShoulder(django.conf.settings.SHOULDERS_CROSSREF_TEST)


def getAgentShoulder():
    return _getShoulder(django.conf.settings.SHOULDERS_AGENT)


def _getShoulder(s):
    try:
        return Shoulder.objects.select_related("datacenter").get(prefix=s)
    except Shoulder.DoesNotExist as e:
        logger.warning(f'Shoulder does not exist: {s}')
