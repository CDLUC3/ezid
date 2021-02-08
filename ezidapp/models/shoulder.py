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
import django.core.exceptions
import logging
import threading

import contextlib
import django.db
import django.db.models
import django.db.transaction

import ezidapp.models.store_datacenter
import impl.util
import ezidapp.models.validation

# Deferred imports...
import impl.util2

"""
import config
import log
import util2
"""

_lock = threading.Lock()
_url = None
_username = None
_password = None
_arkTestPrefix = None
_doiTestPrefix = None
_crossrefTestPrefix = None
_agentPrefix = None
_shoulders = None
_datacenters = None  # (symbolLookup, idLookup)


logger = logging.getLogger(__name__)


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
        ezidapp.models.store_datacenter.StoreDatacenter,
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

    isTest = django.db.models.BooleanField(editable=False)
    # Computed value.  True if the shoulder is a test shoulder.

    # Fields previously only in master_shoulders.txt
    shoulder_type = django.db.models.ForeignKey(ShoulderType, null=True)
    registration_agency = django.db.models.ForeignKey(RegistrationAgency, null=True)
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

    def __str__(self):
        return f"{self.name} ({self.prefix})"


def loadConfig(acquireLock=True):
    global _url, _username, _password, _arkTestPrefix, _doiTestPrefix
    global _agentPrefix, _shoulders, _datacenters
    global _crossrefTestPrefix
    import impl.config

    es = contextlib.ExitStack()

    if acquireLock:
        # noinspection PyTypeChecker
        es.enter_context(_lock)

    with es:
        _url = impl.config.get("shoulders.url")
        _username = impl.config.get("shoulders.username")
        if _username != "":
            _password = impl.config.get("shoulders.password")
        else:
            _username = None
            _password = None

        _arkTestPrefix = impl.config.get("shoulders.ark_test")
        _doiTestPrefix = impl.config.get("shoulders.doi_test")
        _crossrefTestPrefix = impl.config.get("shoulders.crossref_test")
        _agentPrefix = impl.config.get("shoulders.agent")

        _shoulders = dict(
            (s.prefix, s)
            for s in Shoulder.objects.select_related("datacenter").all()
            if s.active and s.manager == 'ezid'
        )

        dc = dict(
            (d.symbol, d)
            for d in ezidapp.models.store_datacenter.StoreDatacenter.objects.all()
        )
        _datacenters = (dc, dict((d.id, d) for d in list(dc.values())))


def getAllShoulders():
    # Returns all shoulders as a list.
    # noinspection PyUnresolvedReferences
    return list(_shoulders.values())


def getLongestShoulderMatch(identifier):
    # Returns the longest shoulder that matches 'identifier', i.e., that
    # is a prefix of 'identifier', or None.
    lm = None
    # noinspection PyUnresolvedReferences
    for s in list(_shoulders.values()):
        if identifier.startswith(s.prefix):
            if lm is None or len(s.prefix) > len(lm.prefix):
                lm = s
    return lm


def getExactShoulderMatch(prefix):
    # Returns the shoulder having prefix 'prefix', or None.
    # noinspection PyUnresolvedReferences
    shoulder_model = _shoulders.get(prefix, None)
    if not shoulder_model:
        # noinspection PyTypeChecker
        logger.debug(
            'Shoulder lookup from cache failed. prefix="{}" len(_shoulders)={}'.format(
                prefix, len(_shoulders)
            )
        )
    return shoulder_model


def getArkTestShoulder():
    # Returns the ARK test shoulder.
    # noinspection PyUnresolvedReferences
    return _shoulders[_arkTestPrefix]


def getDoiTestShoulder():
    # Returns the DOI test shoulder.
    # noinspection PyUnresolvedReferences
    return _shoulders[_doiTestPrefix]


def getCrossrefTestShoulder():
    # Returns the Crossref test shoulder.
    # noinspection PyUnresolvedReferences
    return _shoulders[_crossrefTestPrefix]


def getAgentShoulder():
    # Returns the shoulder used to mint agent persistent identifiers.
    # noinspection PyUnresolvedReferences
    return _shoulders[_agentPrefix]


def getDatacenterBySymbol(symbol):
    # Returns the datacenter having the given symbol.
    try:
        # noinspection PyUnresolvedReferences
        return _datacenters[0][symbol]
    except Exception:
        # Should never happen.
        raise ezidapp.models.store_datacenter.StoreDatacenter.DoesNotExist(
            f"No StoreDatacenter for symbol='{symbol}'."
        )


def getDatacenterById(id_str):
    # Returns the datacenter identified by internal identifier 'id'.
    try:
        # noinspection PyUnresolvedReferences
        return _datacenters[1][id_str]
    except Exception:
        # Should never happen.
        raise ezidapp.models.store_datacenter.StoreDatacenter.DoesNotExist(
            f"No StoreDatacenter for id={id_str:d}."
        )
