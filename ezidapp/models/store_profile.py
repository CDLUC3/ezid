# =============================================================================
#
# EZID :: ezidapp/models/store_profile.py
#
# Database model for profiles in the store database.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2017, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.db.utils

from . import profile


class StoreProfile(profile.Profile):
    pass


# The following caches are only added to or replaced entirely;
# existing entries are never modified.  Thus, with appropriate coding
# below, they are threadsafe without needing locking.

_caches = None  # (labelCache, idCache)


def clearCaches():
    global _caches
    _caches = None


def _getCaches():
    global _caches
    caches = _caches
    if caches == None:
        labelCache = dict((p.label, p) for p in StoreProfile.objects.all())
        idCache = dict((p.id, p) for p in list(labelCache.values()))
        caches = (labelCache, idCache)
        _caches = caches
    return caches


def getByLabel(label):
    # Returns the profile having the given label.  If there's no such
    # profile, a new profile is created and inserted in the database.
    labelCache, idCache = _getCaches()
    if label not in labelCache:
        try:
            p = StoreProfile(label=label)
            p.full_clean(validate_unique=False)
            p.save()
        except django.db.utils.IntegrityError:
            # Somebody beat us to it.
            p = StoreProfile.objects.get(label=label)
        labelCache[label] = p
        idCache[p.id] = p
    return labelCache[label]


def getById(id):
    # Returns the profile identified by internal identifier 'id'.
    labelCache, idCache = _getCaches()
    if id not in idCache:
        p = StoreProfile.objects.get(id=id)
        labelCache[p.label] = p
        idCache[id] = p
    return idCache[id]
