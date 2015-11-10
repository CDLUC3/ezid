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

import django.core.exceptions
import django.db.models
import re
import time

import custom_fields
import util
import validation

# Deferred imports...
"""
import config
import crossref
import datacite
import util2
"""

class Identifier (django.db.models.Model):
  # Describes an identifier.  This class is abstract; there are
  # separate instantiated subclasses of this class for the store and
  # search databases.

  class Meta:
    abstract = True

  identifier = django.db.models.CharField(
    max_length=util.maxIdentifierLength, primary_key=True,
    validators=[validation.anyIdentifier])
  # The identifier in qualified, normalized form, e.g.,
  # "ark:/12345/abc" or "doi:10.1234/ABC".

  @property
  def isArk (self):
    return self.identifier.startswith("ark:/")

  @property
  def isDoi (self):
    return self.identifier.startswith("doi:")

  @property
  def isUrn (self):
    return self.identifier.startswith("urn:")

  @property
  def isUrnUuid (self):
    return self.identifier.startswith("urn:uuid:")

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

  createTime = django.db.models.IntegerField(blank=True, default="",
    validators=[django.core.validators.MinValueValidator(0)])
  # The time the identifier was created as a Unix timestamp.  If not
  # specified, the current time is used.

  updateTime = django.db.models.IntegerField(blank=True, default="",
    validators=[django.core.validators.MinValueValidator(0)])
  # The time the identifier was last modified as a Unix timestamp.  If
  # not specified, the current time is used.

  RESERVED = "R"
  PUBLIC = "P"
  UNAVAILABLE = "U"
  status = django.db.models.CharField(max_length=1,
    choices=[(RESERVED, "reserved"), (PUBLIC, "public"),
    (UNAVAILABLE, "unavailable")], default=PUBLIC)
  # The identifier's status.

  @property
  def isReserved (self):
    return self.status == self.RESERVED

  @property
  def isPublic (self):
    return self.status == self.PUBLIC

  @property
  def isUnavailable (self):
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
  # For DOI identifiers only, the DataCite datacenter at which the
  # identifier is registered (or will be registered when the
  # identifier becomes public, in the case of a reserved identifier);
  # for non-DOI identifiers, None.

  CR_RESERVED = "R"
  CR_WORKING = "B"
  CR_SUCCESS = "S"
  CR_WARNING = "W"
  CR_FAILURE = "F"
  crossrefStatus = django.db.models.CharField(max_length=1, blank=True,
    choices=[(CR_RESERVED, "awaiting status change to public"),
    (CR_WORKING, "registration in progress"),
    (CR_SUCCESS, "successfully registered"),
    (CR_WARNING, "registered with warning"),
    (CR_FAILURE, "registration failure")], default="")
  # For DOI identifiers only, determines (when nonempty) if the
  # identifier is registered with CrossRef (or will be registered when
  # the identifier becomes public, in the case of a reserved
  # identifier), and also indicates the status of the registration
  # process; otherwise, empty.

  @property
  def isCrossref (self):
    return self.crossrefStatus != ""

  @property
  def isCrossrefGood (self):
    return self.crossrefStatus in [self.CR_RESERVED, self.CR_WORKING,
      self.CR_SUCCESS]

  @property
  def isCrossrefBad (self):
    return self.crossrefStatus in [self.CR_WARNING, self.CR_FAILURE]

  crossrefMessage = django.db.models.TextField(blank=True, default="")
  # For the CR_WARNING and CR_FAILURE CrossRef statuses only, any
  # message received from CrossRef; otherwise, empty.

  target = django.db.models.URLField(max_length=2000, blank=True, default="")
  # The identifier's nominal target URL, e.g., "http://foo.com/bar".
  # (The target URL actually registered with resolvers depends on the
  # identifier's status.)  Note that EZID supplies a default target
  # URL that incorporates the identifier in it, so this field will in
  # practice never be empty.  The length limit of 2000 characters is
  # not arbitrary, but is the de facto limit accepted by most web
  # browsers.

  @property
  def defaultTarget (self):
    import util2
    return util2.defaultTargetUrl(self.identifier)

  @property
  def resolverTarget (self):
    # The URL the identifier actually resolves to.
    import util2
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

  @property
  def defaultProfile (self):
    # Should return the default profile for the identifier's type;
    # must be implemented by the concrete subclass.
    assert False, "missing implementation"

  @property
  def usesCrossrefProfile (self):
    return self.profile.label == "crossref"

  @property
  def usesDataciteProfile (self):
    return self.profile.label == "datacite"

  @property
  def usesDublinCoreProfile (self):
    return self.profile.label == "dc"

  @property
  def usesErcProfile (self):
    return self.profile.label == "erc"

  cm = custom_fields.CompressedJsonField(default=lambda: {})
  # All of the identifier's citation metadata as a dictionary of
  # name/value pairs, e.g., { "erc.who": "Proust, Marcel", ... }.

  USER = "U"
  GROUP = "G"
  agentRole = django.db.models.CharField(max_length=1, blank=True,
    choices=[(USER, "user"), (GROUP, "group")], default="")
  # If the identifier is the persistent identifier of an agent, the
  # agent's role; otherwise, empty.

  @property
  def isAgentPid (self):
    return self.agentRole != ""

  isTest = django.db.models.BooleanField(editable=False)
  # Computed value: True if the identifier is a test identifier.

  def my_full_clean (self, exclude=None, validate_unique=False):
    # This method differs from the Django-supplied full_clean method
    # in two ways: it stops if any field-level validations fail; and
    # the default value for the validate_unique argument is False.
    if exclude is None:
      exclude = []
    else:
      exclude = list(exclude)
    self.clean_fields(exclude=exclude)
    self.clean()
    if validate_unique: self.validate_unique(exclude=exclude)

  def clean (self):
    self.baseClean()
    if self.isAgentPid: self.cleanAgentPid()
    self.cleanCitationMetadataFields()
    self.checkMetadataRequirements()
    self.computeComputedValues()

  def baseClean (self):
    if self.owner != None and self.ownergroup == None:
      self.ownergroup = self.owner.group
    else:
      if (self.owner != None) ^ (self.ownergroup != None):
        e = "Owner/ownergroup inconsistency."
        raise django.core.exceptions.ValidationError(
          { "owner": e, "ownergroup": e })
      if self.ownergroup != None:
        if self.ownergroup != self.owner.group:
          raise django.core.exceptions.ValidationError(
            { "ownergroup": "Identifier's ownergroup does not match " +\
            "identifier's owner's group." })
    t = int(time.time())
    if self.createTime == "": self.createTime = t
    if self.updateTime == "": self.updateTime = t
    if self.updateTime < self.createTime:
      raise django.core.exceptions.ValidationError(
        { "updateTime": "Update time precedes creation time." })
    self.unavailableReason = self.unavailableReason.strip()
    if self.unavailableReason != "" and not self.isUnavailable:
      raise django.core.exceptions.ValidationError(
        { "unavailableReason": "Non-unavailable identifier has nonempty " +\
        "unavailability reason." })
    self.crossrefMessage = self.crossrefMessage.strip()
    if self.isDoi:
      if self.datacenter == None:
        raise django.core.exceptions.ValidationError(
          { "datacenter": "Missing datacenter." })
      if self.isCrossref:
        try:
          validation.crossrefDoi(self.identifier)
        except django.core.exceptions.ValidationError, e:
          raise django.core.exceptions.ValidationError({ "identifier": e })
        if not self.exported:
          raise django.core.exceptions.ValidationError(
            { "exported": "CrossRef-registered identifier must be exported." })
        if self.isReserved ^ (self.crossrefStatus == self.CR_RESERVED):
          e = "Identifier status/CrossRef status inconsistency."
          raise django.core.exceptions.ValidationError(
            { "status": e, "crossrefStatus": e })
        if self.isCrossrefGood and self.crossrefMessage != "":
          raise django.core.exceptions.ValidationError(
            { "crossrefMessage": "Non-problematic CrossRef-registered " +\
            "DOI has nonempty CrossRef message." })
      else:
        if self.crossrefMessage != "":
          raise django.core.exceptions.ValidationError(
            { "crossrefMessage": "Non-CrossRef-registered DOI has " +\
            "nonempty CrossRef message." })
    else:
      if self.datacenter != None:
        raise django.core.exceptions.ValidationError(
          { "datacenter": "Non-DOI identifier has datacenter." })
      if self.isCrossref:
        raise django.core.exceptions.ValidationError(
          { "crossrefStatus":
          "Only DOI identifiers may be registered with CrossRef." })
      if self.crossrefMessage != "":
        raise django.core.exceptions.ValidationError(
          { "crossrefMessage": "Non-DOI identifier has nonempty " +\
          "CrossRef message." })
    if self.target == "": self.target = self.defaultTarget
    if self.profile == None: self.profile = self.defaultProfile
    for k, v in self.cm.items():
      if k.strip() != k or k == "" or k.startswith("_"):
        raise django.core.exceptions.ValidationError(
          { "cm": "Invalid citation metadata key." })
      vs = v.strip()
      if vs == "":
        del self.cm[k]
      elif vs != v:
        self.cm[k] = vs

  def cleanAgentPid (self):
    # Checks applicable to agent PIDs only.
    import config
    import util2
    if not self.isArk:
      raise django.core.exceptions.ValidationError(
        { "identifier": "Agent PID is not an ARK." })
    if self.owner == None or\
      self.owner.username != config.get("ldap.admin_username"):
      raise django.core.exceptions.ValidationError(
        { "owner": "Agent PID is not owned by the EZID administrator." })
    if not self.isPublic:
      raise django.core.exceptions.ValidationError(
        { "status": "Agent PID is not public." })
    if self.exported:
      raise django.core.exceptions.ValidationError(
        { "exported": "Agent PID is exported." })
    if self.target != self.defaultTarget:
      raise django.core.exceptions.ValidationError(
        { "target": "Agent PID has non-default target URL." })
    # N.B.: the isTest field hasn't been computed yet.
    if util2.isTestIdentifier(self.identifier):
      raise django.core.exceptions.ValidationError(
        { "identifier": "Agent PID is a test identifier." })

  def cleanCitationMetadataFields (self):
    # Cleans certain citation metadata fields on which EZID imposes
    # structure.
    import crossref
    import datacite
    if "datacite.resourcetype" in self.cm:
      try:
        self.cm["datacite.resourcetype"] =\
          validation.resourceType(self.cm["datacite.resourcetype"])
      except django.core.exceptions.ValidationError, e:
        raise django.core.exceptions.ValidationError(
          { "datacite.resourcetype": e })
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
        self.cm["datacite"] = datacite.validateDcmsRecord(self.identifier,
          self.cm["datacite"], schemaValidate=(not self.isReserved))
      except AssertionError, e:
        raise django.core.exceptions.ValidationError({ "datacite":
          "Metadata validation error: %s." % util.oneLine(str(e)) })
    if "crossref" in self.cm:
      try:
        # Our validation of CrossRef XML records is incomplete (the
        # schema is way too complicated).  As with DataCite XML
        # records, we simply require that they be well-formed and that
        # the parts that EZID cares about are present and sufficiently
        # correct to support our processing.
        self.cm["crossref"] = crossref.validateBody(self.cm["crossref"])
        if not self.isReserved:
          self.cm["crossref"] = crossref.replaceTbas(self.cm["crossref"],
            self.identifier, self.resolverTarget)
      except AssertionError, e:
        raise django.core.exceptions.ValidationError({ "crossref":
          "Metadata validation error: %s." % util.oneLine(str(e)) })

  def checkMetadataRequirements (self):
    import datacite
    if self.isDoi and not self.isReserved:
      # If the identifier has DataCite or CrossRef XML metadata, we
      # know automatically that metadata requirements are satisfied
      # (in the CrossRef case, by virtue of the design of the
      # CrossRef-to-DataCite transform, which always generates a
      # complete DataCite record).
      if "datacite" not in self.cm and\
        (not self.usesCrossrefProfile or "crossref" not in self.cm):
        try:
          self.cm["_profile"] = self.profile.label
          datacite.formRecord(self.identifier, self.cm)
        except AssertionError, e:
          raise django.core.exceptions.ValidationError(
            "Public DOI metadata requirements not satisfied: %s." % str(e))
        finally:
          del self.cm["_profile"]
    if self.isCrossref and "crossref" not in self.cm:
      raise django.core.exceptions.ValidationError(
        "Registration with CrossRef requires CrossRef metadata supplied " +\
        "as value of element 'crossref'.")

  def computeComputedValues (self):
    import util2
    self.isTest = util2.isTestIdentifier(self.identifier)

  def __unicode__ (self):
    return self.identifier

  def toLegacy (self):
    # Returns a legacy representation of the identifier.  See the
    # inverse of this method, 'fromLegacy' below.
    d = self.cm.copy()
    d["_o"] = self.owner.pid
    d["_g"] = self.ownergroup.pid
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
    if not self.exported: d["_x"] = "no"
    if not self.isArk:
      d["_s"] = self.identifier
      d["_su"] = d["_u"]
      d["_st"] = d["_t"]
      if not self.isPublic: d["_st1"] = d["_t1"]
      if self.isDoi: d["_d"] = self.datacenter.symbol
    if self.isCrossref:
      d["_cr"] = "yes | " + self.get_crossrefStatus_display()
      if self.crossrefMessage != "": d["_cr"] += " | " + self.crossrefMessage
    if self.isAgentPid:
      d["_ezid_role"] = "user" if self.agentRole == self.USER else "group"
    return d

  _legacyUnavailableStatusRE = re.compile("unavailable \| (.*)")

  def fromLegacy (self, d):
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
    if self.isArk:
      self.updateTime = int(d["_u"])
    else:
      self.updateTime = int(d["_su"])
    if "_is" in d:
      if d["_is"] == "reserved":
        self.status = self.RESERVED
      else:
        self.status = self.UNAVAILABLE
        m = self._legacyUnavailableStatusRE.match(d["_is"])
        if m: self.unavailableReason = m.group(1)
      if self.isArk:
        self.target = d["_t1"]
      else:
        self.target = d["_st1"]
    else:
      self.status = self.PUBLIC
      if self.isArk:
        self.target = d["_t"]
      else:
        self.target = d["_st"]
    self.exported = "_x" not in d
    for k, v in d.items():
      if not k.startswith("_"): self.cm[k] = v
    if "_cr" in d:
      statuses = dict((v, k) for k, v in\
        self._meta.get_field("crossrefStatus").get_choices())
      assert d["_cr"].startswith("yes | "), "malformed legacy CrossRef status"
      l = [s for s in statuses.keys() if d["_cr"][6:].startswith(s)]
      assert len(l) == 1, "unrecognized legacy CrossRef status"
      self.crossrefStatus = statuses[l[0]]
      if len(d["_cr"]) > 6+len(l[0]):
        m = d["_cr"][6+len(l[0]):]
        assert m.startswith(" | "), "malformed legacy CrossRef status"
        self.crossrefMessage = m[3:]
    if "_ezid_role" in d:
      self.agentRole = self.USER if d["_ezid_role"] == "user" else self.GROUP
