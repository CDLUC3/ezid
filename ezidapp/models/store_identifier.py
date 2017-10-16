# =============================================================================
#
# EZID :: ezidapp/models/store_identifier.py
#
# Database model for identifiers in the store database.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2017, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.db.models

import custom_fields
import identifier
import store_datacenter
import store_group
import store_profile
import store_user

# Deferred imports...
"""
import util2
"""

class StoreIdentifier (identifier.Identifier):
  # An identifier as stored in the store database.

  # Foreign key declarations.  For performance we do not validate
  # foreign key references (but of course they're still checked in the
  # database).

  owner = custom_fields.NonValidatingForeignKey(store_user.StoreUser,
    blank=True, null=True, on_delete=django.db.models.PROTECT)
  ownergroup = custom_fields.NonValidatingForeignKey(store_group.StoreGroup,
    blank=True, null=True, default=None, on_delete=django.db.models.PROTECT)
  datacenter = custom_fields.NonValidatingForeignKey(
    store_datacenter.StoreDatacenter, blank=True, null=True,
    default=None, on_delete=django.db.models.PROTECT)
  profile = custom_fields.NonValidatingForeignKey(store_profile.StoreProfile,
    blank=True, null=True, default=None, on_delete=django.db.models.PROTECT)

  @property
  def defaultProfile (self):
    import util2
    return store_profile.getByLabel(util2.defaultProfile(self.identifier))
