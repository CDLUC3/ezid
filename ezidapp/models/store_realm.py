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

import realm

class StoreRealm (realm.Realm):

  @property
  def groups (self):
    # Returns a Django related manager for the set of groups in this
    # realm.
    return self.storegroup_set

  class Meta:
    verbose_name = "realm"
    verbose_name_plural = "realms"
