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

import util
from . import validation


class Datacenter(django.db.models.Model):
    # A DataCite datacenter.

    class Meta:
        abstract = True

    symbol = django.db.models.CharField(
        max_length=util.maxDatacenterSymbolLength,
        unique=True,
        validators=[validation.datacenterSymbol],
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

    def __unicode__(self):
        return self.symbol
