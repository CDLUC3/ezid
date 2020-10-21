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
import threading

import contextlib2
import django.db
import django.db.models
import django.db.transaction

import store_datacenter
import util
import validation

# Deferred imports...
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
        max_length=util.maxIdentifierLength,
        unique=True,
        validators=[validation.shoulder],
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

    name = django.db.models.CharField(max_length=255, validators=[validation.nonEmpty])
    # The shoulder's name, e.g., "Brown University Library".

    minter = django.db.models.URLField(max_length=255, blank=True)
    # The absolute URL of the associated minter, or empty if none.

    datacenter = django.db.models.ForeignKey(
        store_datacenter.StoreDatacenter,
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
        import util2

        self.type = self.prefix.split(":")[0].upper()
        self.name = self.name.strip()
        if self.isDoi:
            if self.crossrefEnabled:
                if self.datacenter != None:
                    raise django.core.exceptions.ValidationError(
                        {"datacenter": "Non-DataCite DOI shoulder has datacenter."}
                    )
            else:
                if self.datacenter == None:
                    raise django.core.exceptions.ValidationError(
                        {"datacenter": "Missing datacenter."}
                    )
        else:
            if self.datacenter != None:
                raise django.core.exceptions.ValidationError(
                    {"datacenter": "Non-DOI shoulder has datacenter."}
                )
            if self.crossrefEnabled:
                raise django.core.exceptions.ValidationError(
                    {"crossrefEnabled": "Only DOI shoulders may be Crossref enabled."}
                )
        self.isTest = util2.isTestIdentifier(self.prefix)

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.prefix)


def loadConfig(acquireLock=True):
    global _url, _username, _password, _arkTestPrefix, _doiTestPrefix
    global _agentPrefix, _shoulders, _datacenters
    global _crossrefTestPrefix
    import config

    es = contextlib2.ExitStack()

    if acquireLock:
        es.enter_context(_lock)

    with es:
        _url = config.get("shoulders.url")
        _username = config.get("shoulders.username")
        if _username != "":
            _password = config.get("shoulders.password")
        else:
            _username = None
            _password = None

        _arkTestPrefix = config.get("shoulders.ark_test")
        _doiTestPrefix = config.get("shoulders.doi_test")
        _crossrefTestPrefix = config.get("shoulders.crossref_test")
        _agentPrefix = config.get("shoulders.agent")

        _shoulders = dict(
            (s.prefix, s)
            for s in Shoulder.objects.select_related("datacenter").all()
            if s.active and s.manager == 'ezid'
        )

        dc = dict((d.symbol, d) for d in store_datacenter.StoreDatacenter.objects.all())
        _datacenters = (dc, dict((d.id, d) for d in dc.values()))


def getAll():
    # Returns all shoulders as a list.
    return _shoulders.values()


def getLongestMatch(identifier):
    # Returns the longest shoulder that matches 'identifier', i.e., that
    # is a prefix of 'identifier', or None.
    lm = None
    for s in _shoulders.itervalues():
        if identifier.startswith(s.prefix):
            if lm is None or len(s.prefix) > len(lm.prefix):
                lm = s
    return lm


def getExactMatch(prefix):
    # Returns the shoulder having prefix 'prefix', or None.
    shoulder_model = _shoulders.get(prefix, None)
    if not shoulder_model:
        logger.debug(
            'Shoulder lookup from cache failed. prefix="{}" len(_shoulders)={}'.format(
                prefix, len(_shoulders)
            ))
    return shoulder_model


def getArkTestShoulder():
    # Returns the ARK test shoulder.
    return _shoulders[_arkTestPrefix]


def getDoiTestShoulder():
    # Returns the DOI test shoulder.
    return _shoulders[_doiTestPrefix]


def getCrossrefTestShoulder():
    # Returns the Crossref test shoulder.
    return _shoulders[_crossrefTestPrefix]


def getAgentShoulder():
    # Returns the shoulder used to mint agent persistent identifiers.
    return _shoulders[_agentPrefix]


def getDatacenterBySymbol(symbol):
    # Returns the datacenter having the given symbol.
    try:
        return _datacenters[0][symbol]
    except Exception:
        # Should never happen.
        raise store_datacenter.StoreDatacenter.DoesNotExist(
            "No StoreDatacenter for symbol='%s'." % symbol
        )


def getDatacenterById(id):
    # Returns the datacenter identified by internal identifier 'id'.
    try:
        return _datacenters[1][id]
    except:
        # Should never happen.
        raise store_datacenter.StoreDatacenter.DoesNotExist(
            "No StoreDatacenter for id=%d." % id
        )
