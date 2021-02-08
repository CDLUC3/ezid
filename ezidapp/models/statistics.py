# =============================================================================
#
# EZID :: ezidapp/models/statistics.py
#
# Identifier statistics.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2017, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import ezidapp.models.realm
import django.core.validators
import django.db.models

import impl.util
from . import validation


class Statistics(django.db.models.Model):
    # Stores identifier statistics.  Each row contains a descriptor of a
    # unique class of identifiers (a combination of creation month,
    # owner, identifier type, ...) and the count of identifiers in that
    # class.  Note that test identifiers (and therefore
    # anonymously-owned identifiers) are not included.  Reserved
    # identifiers are included, however.

    month = django.db.models.CharField(max_length=7, db_index=True)
    # A creation month in the syntax YYYY-MM.

    owner = django.db.models.CharField(
        max_length=impl.util.maxIdentifierLength, validators=[validation.agentPid]
    )
    # An identifier owner as a persistent identifier, e.g.,
    # "ark:/99166/foo".  Owners are identified by PIDs and not by
    # foreign keys to avoid hard database dependencies.

    ownergroup = django.db.models.CharField(
        max_length=impl.util.maxIdentifierLength, validators=[validation.agentPid]
    )
    # The owner's group as a persistent identifier, e.g.,
    # "ark:/99166/bar".  Groups are identified by PIDs and not by
    # foreign keys to avoid hard database dependencies.

    # noinspection PyProtectedMember
    realm = django.db.models.CharField(
        max_length=ezidapp.models.realm.Realm._meta.get_field("name").max_length
    )
    # The owner's realm as a simple name, e.g., "CDL".  Realms are
    # identified by names and not by foreign keys to avoid hard database
    # dependencies.

    type = django.db.models.CharField(max_length=32)
    # An identifier type, e.g., "ARK" or "DOI".

    hasMetadata = django.db.models.BooleanField()
    # Indicates if identifiers in the class have metadata or not.

    count = django.db.models.IntegerField(
        validators=[django.core.validators.MinValueValidator(0)]
    )
    # The number of identifiers in the class.

    class Meta:
        unique_together = ("month", "owner", "type", "hasMetadata")
