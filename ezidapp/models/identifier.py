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
import time

import custom_fields
import util
import validation

# Deferred imports...
"""
import config
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

  unavailableReason = django.db.models.CharField(max_length=255, blank=True,
    default="")
  # If the status is UNAVAILABLE then, optionally, a reason for the
  # unavailability, e.g., "withdrawn"; otherwise, empty.

  export = django.db.models.BooleanField(default=True)
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

  crossref = django.db.models.BooleanField(default=False)
  # For DOI identifiers only, determines if the identifier is
  # registered with CrossRef (or will be registered when the
  # identifier becomes public, in the case of a reserved identifier);
  # for non-DOI identifiers, False.

  crossrefStatus = django.db.models.TextField(blank=True, default="",
    validators=[validation.crossrefStatusOrEmpty])
  # If 'crossref' is True, the status of the registration process;
  # otherwise, empty.

  target = django.db.models.URLField(max_length=255, blank=True, default="")
  # The identifier's nominal target URL, e.g., "http://foo.com/bar".
  # (The target URL actually registered with resolvers depends on the
  # identifier's status.)  Note that EZID supplies a default target
  # URL that incorporates the identifier in it, so this field will in
  # practice never be empty.

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
    # must be implemented by the subclass.
    assert False, "not implemented"

  # Citation metadata follows.  Which is to say, the following
  # metadata refers to the resource identified by the identifier, not
  # the identifier itself.

  cm = custom_fields.CompressedJsonField(default=lambda: {})
  # All of the identifier's citation metadata as a dictionary of
  # name/value pairs, e.g., { "erc.who": "Proust, Marcel", ... }.

  resourceTitle = django.db.models.TextField(editable=False)
  # Computed value: the resource's title, if available, as mapped from
  # the identifier's preferred metadata profile; otherwise, empty.

  resourceCreator = django.db.models.TextField(editable=False)
  # Computed value: the resource's creator, if available, as mapped
  # from the identifier's preferred metadata profile; otherwise,
  # empty.

  resourcePublisher = django.db.models.TextField(editable=False)
  # Computed value: the resource's publisher, if available, as mapped
  # from the identifier's preferred metadata profile; otherwise,
  # empty.

  resourcePublicationDate = django.db.models.CharField(max_length=10,
    editable=False)
  # Computed value: the resource's publication date, if available, as
  # mapped from the identifier's preferred metadata profile;
  # otherwise, empty.  A nonempty publication date may take one of
  # three forms: YYYY, YYYY-MM, or YYYY-MM-DD.

  resourceType = django.db.models.CharField(max_length=1, editable=False,
    choices=sorted([(v, k) for k, v in validation.resourceTypes.items()],
    cmp=lambda a, b: cmp(a[1], b[1])))
  # Computed value: the resource's type, if available, as mapped from
  # the identifier's preferred metadata profile; otherwise, empty.
  # The type is stored as a single-character mnemonic code.

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

  hasIssues = django.db.models.BooleanField(editable=False)
  # Computed value: True if the identifier "has issues," i.e., has
  # problems of some kind.

  def issueReasons (self):
    # Returns a list of the identifier's issues.
    reasons = []
    if not self.hasMetadata: reasons.append("missing metadata")
    if self.crossref:
      if validation.badCrossrefStatusRE.match(self.crossrefStatus):
        reasons.append("CrossRef registration " +\
          ("warning" if "warning" in self.crossrefStatus else "failure"))
    return reasons

  def my_full_clean (self, exclude=None, validate_unique=False):
    # This method differs from the Django-supplied full_clean method
    # in three ways: it stops if any field-level validations fail; it
    # computes the computed values; and the default value for the
    # validate_unique argument is False.
    if exclude is None:
      exclude = []
    else:
      exclude = list(exclude)
    self.clean_fields(exclude=exclude)
    self.clean()
    self.computeComputedValues()
    if validate_unique: self.validate_unique(exclude=exclude)

  def clean (self):
    # N.B.: This method does not examine any computed values, nor does
    # it examine the citation metadata.  For validations related to
    # those, computeComputedValues must be called.
    import util2
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
    self.crossrefStatus = self.crossrefStatus.strip()
    if self.isDoi:
      if self.datacenter == None:
        raise django.core.exceptions.ValidationError(
          { "datacenter": "Missing datacenter." })
      if self.crossref:
        if self.crossrefStatus == "":
          raise django.core.exceptions.ValidationError(
            { "crossrefStatus": "Missing CrossRef status." })
      else:
        if self.crossrefStatus != "":
          raise django.core.exceptions.ValidationError(
            { "crossrefStatus": "Non-CrossRef-registered DOI has " +\
            "nonempty CrossRef status." })
    else:
      if self.datacenter != None:
        raise django.core.exceptions.ValidationError(
          { "datacenter": "Non-DOI identifier has datacenter." })
      if self.crossref:
        raise django.core.exceptions.ValidationError(
          { "crossref": "Non-DOI identifier registered with CrossRef." })
      if self.crossrefStatus != "":
        raise django.core.exceptions.ValidationError(
          { "crossrefStatus": "Non-DOI identifier has nonempty " +\
          "CrossRef status." })
    if self.target == "": self.target = self.defaultTarget
    self.isTest = util2.isTestIdentifier(self.identifier)
    if self.isAgentPid: self.cleanAgentPid()
    if self.profile == None: self.profile = self.defaultProfile

  def cleanAgentPid (self):
    # Checks applicable to agent PIDs only.
    import config
    if not self.isArk:
      raise django.core.exceptions.ValidationError(
        { "identifier": "Agent PID is not an ARK." })
    if self.owner == None or\
      self.owner.username != config.config("ldap.admin_username"):
      raise django.core.exceptions.ValidationError(
        { "owner": "Agent PID is not owned by the EZID administrator." })
    if not self.isPublic:
      raise django.core.exceptions.ValidationError(
        { "status": "Agent PID is not public." })
    if self.export:
      raise django.core.exceptions.ValidationError(
        { "export": "Agent PID is exported." })
    if self.target != self.defaultTarget:
      raise django.core.exceptions.ValidationError(
        { "target": "Agent PID has non-default target URL." })
    if self.isTest:
      raise django.core.exceptions.ValidationError(
        { "identifier": "Agent PID is a test identifier." })

  def computeComputedValues (self):
    # This method should be called after clean_fields and clean.  Note
    # that it, too, can raise validation exceptions.
    self.resourceType = ""
    self.resourceTitle = ""
    self.resourceCreator = ""
    self.resourcePublisher = ""
    self.resourcePublicationDate = ""
    if "datacite.resourcetype" in self.cm:
      v = validation.resourceType(self.cm["datacite.resourcetype"])
      self.resourceType = v[0]
      self.cm["datacite.resourcetype"] = v[1]
    self.hasMetadata = self.resourceTitle != "" and\
      self.resourcePublicationDate != "" and (self.resourceCreator != "" or\
      self.resourcePublisher != "")
    self.publicSearchVisible = self.isPublic and self.export and\
      not self.isTest
    self.oaiVisible = self.publicSearchVisible and self.hasMetadata and\
      self.target != self.defaultTarget
    self.hasIssues = not self.hasMetadata or (self.crossref and\
      validation.badCrossrefStatusRE.match(self.crossrefStatus))

  def __unicode__ (self):
    return self.identifier
