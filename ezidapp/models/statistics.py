#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Identifier statistics
"""

# import ezidapp.models.realm
import django.core.validators
import django.db.models

import ezidapp.models.realm
import impl.util
from . import validation


class Statistics(django.db.models.Model):
    """Store identifier statistics

    Each row contains a descriptor of a unique class of identifiers (a combination of creation
    month, owner, identifier type, ...) and the count of identifiers in that class.

    Test identifiers (and therefore anonymously-owned identifiers) are not included.  Reserved
    identifiers are included, however.
    """
    class Meta:
        unique_together = ("month", "owner", "type", "hasMetadata")


    # A creation month in the syntax YYYY-MM.
    month = django.db.models.CharField(max_length=7, db_index=True)

    # An identifier owner as a persistent identifier, e.g.,
    # "ark:/99166/foo".  Owners are identified by PIDs and not by
    # foreign keys to avoid hard database dependencies.
    owner = django.db.models.CharField(
        max_length=impl.util.maxIdentifierLength, validators=[validation.agentPid]
    )

    # The owner's group as a persistent identifier, e.g.,
    # "ark:/99166/bar".  Groups are identified by PIDs and not by
    # foreign keys to avoid hard database dependencies.
    ownergroup = django.db.models.CharField(
        max_length=impl.util.maxIdentifierLength, validators=[validation.agentPid]
    )

    # noinspection PyProtectedMember
    # The owner's realm as a simple name, e.g., "CDL".  Realms are
    # identified by names and not by foreign keys to avoid hard database
    # dependencies.
    realm = django.db.models.CharField(
        max_length=ezidapp.models.realm.Realm._meta.get_field("name").max_length
    )

    # An identifier type, e.g., "ARK" or "DOI".
    type = django.db.models.CharField(max_length=32)

    # Indicates if identifiers in the class have metadata or not.
    hasMetadata = django.db.models.BooleanField()

    # The number of identifiers in the class.
    count = django.db.models.IntegerField(
        validators=[django.core.validators.MinValueValidator(0)]
    )
