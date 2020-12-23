# =============================================================================
#
# EZID :: ezidapp/models/store_datacenter.py
#
# Database model for DataCite datacenters in the store database.
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

from . import datacenter
from . import validation


class StoreDatacenter(datacenter.Datacenter):
    # A DataCite datacenter as stored in the store database.

    name = django.db.models.CharField(
        max_length=255, unique=True, validators=[validation.nonEmpty]
    )
    # The datacenter's full name, e.g., "Brown University Library".

    def clean(self):
        super(StoreDatacenter, self).clean()
        self.name = self.name.strip()

    class Meta:
        verbose_name = "datacenter"
        verbose_name_plural = "datacenters"
