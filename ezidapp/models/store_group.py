# =============================================================================
#
# EZID :: ezidapp/models/store_group.py
#
# Database model for groups in the store database.
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

import group
import shoulder
import store_realm
import validation

class StoreGroup (group.Group):

  # Inherited foreign key declarations...
  realm = django.db.models.ForeignKey(store_realm.StoreRealm,
    on_delete=django.db.models.PROTECT)

  organizationName = django.db.models.CharField("name", max_length=255,
    validators=[validation.nonEmpty])
  organizationAcronym = django.db.models.CharField("acronym", max_length=255,
    blank=True)
  organizationUrl = django.db.models.URLField("URL", max_length=255)
  organizationStreetAddress = django.db.models.CharField("street address",
    max_length=255, validators=[validation.nonEmpty])
  # An EZID group is typically associated with some type of
  # organization, institution, or group; these fields describe that
  # entity.

  BACHELORS = "B"
  CORPORATE = "C"
  GROUP = "G"
  INSTITUTION = "I"
  MASTERS = "M"
  NONPAYING = "N"
  accountType = django.db.models.CharField("account type", max_length=1,
    choices=[(BACHELORS, "Associate/bachelors-granting"),
    (CORPORATE, "Corporate"), (GROUP, "Group"),
    (INSTITUTION, "Institution"), (MASTERS, "Masters-granting"),
    (NONPAYING, "Non-paying")], blank=True)
  agreementOnFile = django.db.models.BooleanField("agreement on file",
    default=False)
  # Fields for business purposes only; not used by EZID.

  crossrefEnabled = django.db.models.BooleanField("CrossRef enabled",
    default=False)
  # Determines if users in the group may register identifiers with
  # CrossRef.  Note that CrossRef registration requires the enablement
  # of both the user and the shoulder.

  shoulders = django.db.models.ManyToManyField(shoulder.Shoulder, blank=True)
  # The shoulders to which users in the group have access.  The test
  # shoulders are not included in this relation.

  notes = django.db.models.TextField(blank=True)
  # Any additional notes.

  def clean (self):
    super(StoreGroup, self).clean()
    self.organizationName = self.organizationName.strip()
    self.organizationAcronym = self.organizationAcronym.strip()
    self.organizationStreetAddress = self.organizationStreetAddress.strip()
    self.notes = self.notes.strip()

  class Meta:
    verbose_name = "group"
    verbose_name_plural = "groups"
