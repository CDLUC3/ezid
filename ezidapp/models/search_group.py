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

import ezidapp.models.group

# import ezidapp.models.search_realm


class SearchGroup(ezidapp.models.group.Group):
    realm = django.db.models.ForeignKey(
        'ezidapp.SearchRealm', on_delete=django.db.models.PROTECT
    )
