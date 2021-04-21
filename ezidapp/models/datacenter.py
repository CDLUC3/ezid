# =============================================================================
#
# EZID :: ezidapp/models/datacenter.py
#
# Abstract database model for DataCite datacenters.
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

import ezidapp.models.validation
import ezidapp.models.validation
import impl.util


class Datacenter(django.db.models.Model):
    # import ezidapp.models.validation
    # A DataCite datacenter.

    class Meta:
        abstract = True

    symbol = django.db.models.CharField(
        max_length=impl.util.maxDatacenterSymbolLength,
        unique=True,
        validators=[ezidapp.models.validation.datacenterSymbol],
    )
    # The datacenter's so-called symbol, e.g., "CDL.BUL".

    @property
    def allocator(self):
        return self.symbol.split(".")[0]

    @property
    def datacenter(self):
        return self.symbol.split(".")[1]

    def clean(self):
        self.symbol = self.symbol.upper()

    def __str__(self):
        return self.symbol


class SearchDatacenter(Datacenter):
    pass




class StoreDatacenter(Datacenter):
    # A DataCite datacenter as stored in the store database.

    name = django.db.models.CharField(
        max_length=255, unique=True, validators=[ezidapp.models.validation.nonEmpty]
    )
    # The datacenter's full name, e.g., "Brown University Library".

    def clean(self):
        super(StoreDatacenter, self).clean()
        self.name = self.name.strip()

    class Meta:
        verbose_name = "datacenter"
        verbose_name_plural = "datacenters"
