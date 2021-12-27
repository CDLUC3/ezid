#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Abstract database model for metadata profiles.
"""

import re

import django.core.validators
import django.db.models


class Profile(django.db.models.Model):
    # A metadata profile.

    # class Meta:
    #     abstract = True

    label = django.db.models.CharField(
        max_length=32,
        unique=True,
        validators=[
            django.core.validators.RegexValidator(
                "^[a-z0-9]+([-_.][a-z0-9]+)*$", "Invalid profile name.", flags=re.I
            )
        ],
    )
    # The profile's label, e.g., "erc".

    def clean(self):
        self.label = self.label.strip()

    def __str__(self):
        return self.label


#     if caches is None:
#         labelCache = dict((p.label, p) for p in Profile.objects.all())
#         idCache = dict((p.id, p) for p in list(labelCache.values()))
