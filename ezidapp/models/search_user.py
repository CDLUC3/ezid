# =============================================================================
#
# EZID :: ezidapp/models/search_user.py
#
# Database model for users in the search database.
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

# import ezidapp.models.search_group
# import ezidapp.models.search_realm
import ezidapp.models.user


class SearchUser(ezidapp.models.user.User):
    group = django.db.models.ForeignKey(
        'ezidapp.SearchGroup', on_delete=django.db.models.PROTECT
    )
    realm = django.db.models.ForeignKey(
        'ezidapp.SearchRealm', on_delete=django.db.models.PROTECT
    )
