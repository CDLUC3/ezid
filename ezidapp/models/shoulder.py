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

import base64
import django.db
import django.db.models
import django.db.transaction
import threading
import urllib2
import uuid

import shoulder_parser
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
_agentPrefix = None
_shoulders = None
_datacenters = None # (symbolLookup, idLookup)

class Shoulder (django.db.models.Model):
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

  prefix = django.db.models.CharField(max_length=util.maxIdentifierLength,
    unique=True, validators=[validation.shoulder])
  # The shoulder itself, qualified and normalized, e.g., "ark:/12345/"
  # or "doi:10.1234/FOO".

  type = django.db.models.CharField(max_length=32, editable=False)
  # Computed value: the shoulder's identifier type, e.g., "ARK".  Used
  # only to implement the uniqueness constraint below.

  @property
  def isArk (self):
    return self.type == "ARK"

  @property
  def isDoi (self):
    return self.type == "DOI"

  @property
  def isUuid (self):
    return self.type == "UUID"

  name = django.db.models.CharField(max_length=255,
    validators=[validation.nonEmpty])
  # The shoulder's name, e.g., "Brown University Library".

  minter = django.db.models.URLField(max_length=255, blank=True)
  # The absolute URL of the associated minter, or empty if none.

  datacenter = django.db.models.ForeignKey(store_datacenter.StoreDatacenter,
    blank=True, null=True, default=None, on_delete=django.db.models.PROTECT)
  # For DOI shoulders only, the shoulder's default datacenter;
  # otherwise, None.

  crossrefEnabled = django.db.models.BooleanField("Crossref enabled",
    default=False)
  # For DOI shoulders only, True if the shoulder supports Crossref
  # registration; otherwise, False.

  isTest = django.db.models.BooleanField(editable=False)
  # Computed value.  True if the shoulder is a test shoulder.

  class Meta:
    unique_together = ("name", "type")

  def clean (self):
    import util2
    self.type = self.prefix.split(":")[0].upper()
    self.name = self.name.strip()
    if self.isDoi:
      if self.datacenter == None:
        raise django.core.exceptions.ValidationError(
          { "datacenter": "Missing datacenter." })
    else:
      if self.datacenter != None:
        raise django.core.exceptions.ValidationError(
          { "datacenter": "Non-DOI shoulder has datacenter." })
      if self.crossrefEnabled:
        raise django.core.exceptions.ValidationError(
          { "crossrefEnabled":
          "Only DOI shoulders may be Crossref enabled." })
    self.isTest = util2.isTestIdentifier(self.prefix)

  def __unicode__ (self):
    return "%s (%s)" % (self.name, self.prefix)

def _loadConfig (acquireLock=True):
  global _url, _username, _password, _arkTestPrefix, _doiTestPrefix
  global _agentPrefix, _shoulders, _datacenters
  import config
  if acquireLock: _lock.acquire()
  try:
    _url = config.get("shoulders.url")
    _username = config.get("shoulders.username")
    if _username != "":
      _password = config.get("shoulders.password")
    else:
      _username = None
      _password = None
    _arkTestPrefix = config.get("shoulders.ark_test")
    _doiTestPrefix = config.get("shoulders.doi_test")
    _agentPrefix = config.get("shoulders.agent")
    _shoulders = None
    _datacenters = None
  finally:
    if acquireLock: _lock.release()

def _ensureConfigLoaded ():
  if _url is None:
    import config
    _loadConfig(acquireLock=False)
    config.registerReloadListener(_loadConfig)

def _reconcileShoulders ():
  global _shoulders, _datacenters
  import log
  try:
    stage = "loading"
    f = None
    try:
      r = urllib2.Request(_url)
      if _username != None:
        r.add_header("Authorization", "Basic " +\
          base64.b64encode("%s:%s" % (_username, _password)))
      f = urllib2.urlopen(r)
      fc = f.read().decode("UTF-8")
    finally:
      if f: f.close()
    entries, errors, warnings = shoulder_parser.parse(fc)
    assert len(errors) == 0, "file validation error(s): " +\
      ", ".join("(line %d) %s" % e for e in errors)
    newDatacenters = dict((e.key, e) for e in entries\
      if e.type == "datacenter" and e.manager == "ezid" and e.active)
    newShoulders = dict((e.key, e) for e in entries\
      if e.type == "shoulder" and e.manager == "ezid" and e.active)
    # The following operations must be performed in exactly this order
    # because MySQL enforces integrity constraints after every
    # operation.
    stage = "reconciling with"
    with django.db.transaction.atomic():
      datacenters = dict((d.symbol, d) for d in\
        store_datacenter.StoreDatacenter.objects.all())
      shoulders = dict((s.prefix, s) for s in\
        Shoulder.objects.select_related("datacenter").all())
      # 1. For modified shoulders, replace fields that have UNIQUE
      # constraints with random unique values and foreign keys with
      # NULL; delete shoulders that no longer exist.
      shoulderFixups = []
      for prefix, s in shoulders.items():
        if prefix in newShoulders:
          ns = newShoulders[prefix]
          if s.name != ns.name or s.minter != ns.minter or\
            ((s.datacenter == None and "datacenter" in ns) or\
            (s.datacenter != None and\
            s.datacenter.symbol != ns.get("datacenter", ""))) or\
            (s.crossrefEnabled ^ ns.get("crossref", False)):
            shoulderFixups.append((s, ns.name, ns.minter,
              ns.get("datacenter", None), ns.get("crossref", False)))
            s.name = str(uuid.uuid1())
            s.datacenter = None
            s.save()
        else:
          try:
            # Unfortunately, Django doesn't offer on_delete=PROTECT on
            # many-to-many relationships, so we have to check
            # manually.
            if s.storegroup_set.count() > 0:
              raise django.db.IntegrityError("shoulder is referenced by group")
            s.delete()
          except django.db.IntegrityError, e:
            raise django.db.IntegrityError(
              "error deleting shoulder %s, shoulder is in use: %s" %\
              (s.prefix, util.formatException(e)))
          del shoulders[prefix]
      # 2. Similarly for datacenters.
      datacenterFixups = []
      for symbol, d in datacenters.items():
        if symbol in newDatacenters:
          nd = newDatacenters[symbol]
          if d.name != nd.name:
            datacenterFixups.append((d, nd.name))
            d.name = str(uuid.uuid1())
            d.save()
        else:
          try:
            d.delete()
          except django.db.IntegrityError, e:
            raise django.db.IntegrityError(
              "error deleting datacenter %s, datacenter is in use: %s" %\
              (d.symbol, str(e)))
          del datacenters[symbol]
      # 3. Now apply datacenter fixups.
      for d, name in datacenterFixups:
        d.name = name
        d.full_clean(validate_unique=False)
        d.save()
      # 4. Add new datacenters.
      for symbol, nd in newDatacenters.items():
        if symbol not in datacenters:
          d = store_datacenter.StoreDatacenter(symbol=symbol, name=nd.name)
          d.full_clean(validate_unique=False)
          d.save()
          datacenters[symbol] = d
      # 5. Now apply shoulder fixups.
      for s, name, minter, datacenter, crossrefEnabled in shoulderFixups:
        s.name = name
        s.minter = minter
        if datacenter != None: s.datacenter = datacenters[datacenter]
        s.crossrefEnabled = crossrefEnabled
        s.full_clean(validate_unique=False)
        s.save()
      # 6. Finally, add new shoulders.
      for prefix, ns in newShoulders.items():
        if prefix not in shoulders:
          s = Shoulder(prefix=prefix, name=ns.name, minter=ns.minter,
            crossrefEnabled=ns.get("crossref", False))
          if "datacenter" in ns:
            s.datacenter = datacenters[ns.datacenter]
          else:
            s.datacenter = None
          s.full_clean(validate_unique=False)
          s.save()
          shoulders[prefix] = s
  except Exception, e:
    # Log the error, but otherwise continue to run with the shoulders
    # and datacenters we have.
    log.otherError("shoulder._reconcileShoulders",
      Exception("error %s external shoulder file: %s" % (stage,
      util.formatException(e))))
  with django.db.transaction.atomic():
    # In all cases, to fill the in-memory caches do fresh queries to
    # get proper dependent datacenter objects.
    _shoulders = dict((s.prefix, s) for s in Shoulder.objects.\
      select_related("datacenter").all())
    dc = dict((d.symbol, d) for d in\
      store_datacenter.StoreDatacenter.objects.all())
    _datacenters = (dc, dict((d.id, d) for d in dc.values()))

def _lockAndLoad (f):
  # Decorator.
  def wrapped (*args, **kwargs):
    _lock.acquire()
    try:
      if _shoulders is None:
        _ensureConfigLoaded()
        _reconcileShoulders()
      return f(*args, **kwargs)
    finally:
      _lock.release()
  return wrapped

@_lockAndLoad
def getAll ():
  # Returns all shoulders as a list.
  return _shoulders.values()

@_lockAndLoad
def getLongestMatch (identifier):
  # Returns the longest shoulder that matches 'identifier', i.e., that
  # is a prefix of 'identifier', or None.
  lm = None
  for s in _shoulders.itervalues():
    if identifier.startswith(s.prefix):
      if lm is None or len(s.prefix) > len(lm.prefix): lm = s
  return lm

@_lockAndLoad
def getExactMatch (prefix):
  # Returns the shoulder having prefix 'prefix', or None.
  return _shoulders.get(prefix, None)

@_lockAndLoad
def getArkTestShoulder ():
  # Returns the ARK test shoulder.
  return _shoulders[_arkTestPrefix]

@_lockAndLoad
def getDoiTestShoulder ():
  # Returns the DOI test shoulder.
  return _shoulders[_doiTestPrefix]

@_lockAndLoad
def getAgentShoulder ():
  # Returns the shoulder used to mint agent persistent identifiers.
  return _shoulders[_agentPrefix]

@_lockAndLoad
def getDatacenterBySymbol (symbol):
  # Returns the datacenter having the given symbol.
  try:
    return _datacenters[0][symbol]
  except:
    # Should never happen.
    raise store_datacenter.StoreDatacenter.DoesNotExist(
      "No StoreDatacenter for symbol='%s'." % symbol)

@_lockAndLoad
def getDatacenterById (id):
  # Returns the datacenter identified by internal identifier 'id'.
  try:
    return _datacenters[1][id]
  except:
    # Should never happen.
    raise store_datacenter.StoreDatacenter.DoesNotExist(
      "No StoreDatacenter for id=%d." % id)
