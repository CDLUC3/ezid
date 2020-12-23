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

from . import search_group
from . import search_realm
from . import user


class SearchUser(user.User):
    group = django.db.models.ForeignKey(
        search_group.SearchGroup, on_delete=django.db.models.PROTECT
    )
    realm = django.db.models.ForeignKey(
        search_realm.SearchRealm, on_delete=django.db.models.PROTECT
    )
