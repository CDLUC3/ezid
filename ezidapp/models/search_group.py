# =============================================================================
#
# EZID :: ezidapp/models/search_group.py
#
# Database model for groups in the search database.
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

import group
import search_realm


class SearchGroup(group.Group):
    realm = django.db.models.ForeignKey(
        search_realm.SearchRealm, on_delete=django.db.models.PROTECT
    )
