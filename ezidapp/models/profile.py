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

import django.core.validators
import django.db.models
import re

class Profile (django.db.models.Model):
  # A metadata profile.

  class Meta:
    abstract = True

  label = django.db.models.CharField(max_length=32, unique=True,
    validators=[django.core.validators.RegexValidator(
    "^[a-z0-9]+([-_.][a-z0-9]+)*$", "Invalid profile name.", flags=re.I)])
  # The profile's label, e.g., "erc".

  def clean (self):
    self.label = self.label.strip()

  def __unicode__ (self):
    return self.label
