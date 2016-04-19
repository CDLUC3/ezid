# =============================================================================
#
# EZID :: ezidapp/models/store_realm.py
#
# Database model for realms in the store database.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2016, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.core.validators

import realm

class StoreRealm (realm.Realm):

  @property
  def groups (self):
    # Returns a Django related manager for the set of groups in this
    # realm.
    return self.storegroup_set

  def clean (self):
    super(StoreRealm, self).clean()
    if self.name == "anonymous":
      raise django.core.validators.ValidationError({ "name":
        "The name 'anonymous' is reserved." })

  class Meta:
    verbose_name = "realm"
    verbose_name_plural = "realms"

  isAnonymous = False
  # See below.

class AnonymousRealm (object):
  # A class to represent the realm in which the anonymous user
  # resides.  Note that this class can be used directly--- an object
  # need not be instantiated.
  name = "anonymous"
  isAnonymous = True
