#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Object Relational Mapper (ORM) models for DataCite datacenters
"""

import django.db.models

import ezidapp.models.validation
import impl.util


# A DataCite datacenter.
class Datacenter(django.db.models.Model):
    class Meta:
        verbose_name = "datacenter"
        verbose_name_plural = "datacenters"

    @property
    def allocator(self):
        return self.symbol.split(".")[0]

    @property
    def datacenter(self):
        return self.symbol.split(".")[1]

    def clean(self):
        self.symbol = self.symbol.upper()
        self.name = self.name.strip()

    def __str__(self):
        return self.symbol

    # The datacenter's so-called symbol, e.g., "CDL.BUL".
    symbol = django.db.models.CharField(
        max_length=impl.util.maxDatacenterSymbolLength,
        unique=True,
        validators=[ezidapp.models.validation.datacenterSymbol],
    )

    # The datacenter's full name, e.g., "Brown University Library".
    name = django.db.models.CharField(
        max_length=255, unique=True, validators=[ezidapp.models.validation.nonEmpty]
    )
