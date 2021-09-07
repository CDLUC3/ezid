#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Object Relational Mapper (ORM) models for realms
"""

import django.core.validators
import django.db.models
import django.http

import ezidapp.models.validation


class Realm(django.db.models.Model):
    # An EZID realm, which corresponds to a broad administrative area.

    class Meta:
    #     abstract = True
        verbose_name = "realm"
        verbose_name_plural = "realms"

    name = django.db.models.CharField(
        max_length=32, unique=True, validators=[ezidapp.models.validation.nonEmpty]
    )
    # The realm's name, e.g., "CDL".

    def clean(self):
        self.name = self.name.strip()
        if self.name == "anonymous":
            raise django.core.validators.ValidationError(
                {"name": "The name 'anonymous' is reserved."}
            )

    def __str__(self):
        return self.name

    @property
    def groups(self):
        # Returns a Django related manager for the set of groups in this
        # realm.
        return self.group_set

    isAnonymous = False
    # See below.


class AnonymousRealm(object):
    # The realm in which the anonymous user resides.
    #
    # This class can be used directly. An object need not be instantiated.
    name = "anonymous"
    isAnonymous = True


realmredirect = django.http.HttpResponseRedirect
