# =============================================================================
#
# EZID :: ezidapp/models/realm.py
#
# Abstract database model for realms.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.core.validators
import django.db.models

import ezidapp.models.validation


class Realm(django.db.models.Model):
    # An EZID realm, which corresponds to a broad administrative area.

    class Meta:
        abstract = True

    name = django.db.models.CharField(
        max_length=32, unique=True, validators=[ezidapp.models.validation.nonEmpty]
    )
    # The realm's name, e.g., "CDL".

    def clean(self):
        self.name = self.name.strip()

    def __str__(self):
        return self.name


class StoreRealm(Realm):
    @property
    def groups(self):
        # Returns a Django related manager for the set of groups in this
        # realm.
        return self.storegroup_set

    def clean(self):
        super(StoreRealm, self).clean()
        if self.name == "anonymous":
            raise django.core.validators.ValidationError(
                {"name": "The name 'anonymous' is reserved."}
            )

    class Meta:
        verbose_name = "realm"
        verbose_name_plural = "realms"

    isAnonymous = False
    # See below.


class AnonymousRealm(object):
    # A class to represent the realm in which the anonymous user
    # resides.  Note that this class can be used directly--- an object
    # need not be instantiated.
    name = "anonymous"
    isAnonymous = True


realmredirect = django.http.HttpResponseRedirect


class SearchRealm(Realm):
    pass
