#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Abstract database model for metadata profiles.
"""

import re

import django.core.validators
import django.db.models
import impl.util

import impl
from ezidapp.models import validation


class ProfileCopy(django.db.models.Model):
    label = django.db.models.CharField(
        max_length=32,
        unique=True,
        validators=[
            django.core.validators.RegexValidator(
                "^[a-z0-9]+([-_.][a-z0-9]+)*$", "Invalid profile name.", flags=re.I
            )
        ],
    )

    prefix = django.db.models.CharField(
        max_length=impl.util.maxIdentifierLength,
        unique=True,
        validators=[validation.shoulder],
        default='ark:/99999/fk8'
    )
    # The profile's label, e.g., "erc".

    def clean(self):
        self.label = self.label.strip()

    def __str__(self):
        return self.label


#     if caches is None:
#         labelCache = dict((p.label, p) for p in Profile.objects.all())
#         idCache = dict((p.id, p) for p in list(labelCache.values()))
