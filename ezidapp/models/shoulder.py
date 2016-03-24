# =============================================================================
#
# EZID :: ezidapp/models/shoulder.py
#
# Database model for shoulders in the store database.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2016, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.db.models

import store_datacenter
import util
import validation

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
  # Computed value: the shoulder's identifier type, e.g., "ark".  Used
  # only to implement the uniqueness constraint below.

  @property
  def isArk (self):
    return self.type == "ark"

  @property
  def isDoi (self):
    return self.type == "doi"

  @property
  def isUrn (self):
    return self.type == "urn"

  name = django.db.models.CharField(max_length=255,
    validators=[validation.nonEmpty])
  # The shoulder's name, e.g., "Brown University Library".

  minter = django.db.models.URLField(max_length=255, blank=True,
    validators=[validation.unicodeBmpOnly])
  # The absolute URL of the associated minter, or empty if none.

  datacenter = django.db.models.ForeignKey(store_datacenter.StoreDatacenter,
    blank=True, null=True, default=None, on_delete=django.db.models.PROTECT)
  # For DOI shoulders only, the shoulder's default datacenter;
  # otherwise, None.

  crossrefEnabled = django.db.models.BooleanField("CrossRef enabled",
    default=False)
  # For DOI shoulders only, True if the shoulder supports CrossRef
  # registration; otherwise, False.

  class Meta:
    unique_together = ("name", "type")

  def clean (self):
    self.type = self.prefix.split(":")[0]
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
          "Only DOI shoulders may be CrossRef-enabled." })

  def __unicode__ (self):
    return self.prefix
