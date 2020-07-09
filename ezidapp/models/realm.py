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

import django.db.models

import validation


class Realm(django.db.models.Model):
    # An EZID realm, which corresponds to a broad administrative area.

    class Meta:
        abstract = True

    name = django.db.models.CharField(
        max_length=32, unique=True, validators=[validation.nonEmpty]
    )
    # The realm's name, e.g., "CDL".

    def clean(self):
        self.name = self.name.strip()

    def __unicode__(self):
        return self.name
