# =============================================================================
#
# EZID :: ezidapp/models/profile.py
#
# Abstract database model for metadata profiles.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.db.models

import validation

class Profile (django.db.models.Model):
  # A metadata profile.

  class Meta:
    abstract = True

  label = django.db.models.CharField(max_length=255, unique=True,
    validators=[validation.nonEmpty])
  # The profile's label, e.g., "erc".

  def clean (self):
    self.label = self.label.strip()

  def __unicode__ (self):
    return self.label
