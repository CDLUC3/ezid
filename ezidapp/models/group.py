# =============================================================================
#
# EZID :: ezidapp/models/group.py
#
# Abstract database model for groups.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import re

import django.core.validators
import django.db.models

import ezidapp.models.shoulder
import impl.log
import impl.util
import ezidapp.models.validation
import impl.nog.minter


class Group(django.db.models.Model):
    # An EZID group, which typically corresponds to a paying account or
    # institution.

    class Meta:
        abstract = True

    pid = django.db.models.CharField(
        max_length=impl.util.maxIdentifierLength,
        unique=True,
        validators=[ezidapp.models.validation.agentPidOrEmpty],
    )
    # The group's persistent identifier, e.g., "ark:/99166/foo".  The
    # field will in practice never be empty; rather, if empty, a new
    # persistent identifier is minted (but not created).  Note that the
    # uniqueness requirement is actually stronger than indicated here:
    # it is expected that all agent (i.e., all user and group)
    # persistent identifiers are unique.

    groupname = django.db.models.CharField(
        max_length=32,
        unique=True,
        validators=[
            django.core.validators.RegexValidator(
                "^[a-z0-9]+([-_.][a-z0-9]+)*$", "Invalid groupname.", flags=re.I
            )
        ],
    )
    # The group's groupname, e.g., "dryad".

    # A note on foreign keys: since the store and search databases are
    # completely separate, foreign keys must reference different target
    # models, and so the declaration of all foreign keys is deferred to
    # the concrete subclasses.  There appears to be no better way to
    # model this in Django.

    # realm = django.db.models.ForeignKey(realm.Realm)
    # The group's realm.

    def clean(self):
        if self.pid == "":
            try:
                s = ezidapp.models.shoulder.getAgentShoulder()
                assert s.isArk, "Agent shoulder type must be ARK"
                self.pid = "{}{}".format(s.prefix, impl.nog.minter.mint_id(s))
            except Exception as e:
                impl.log.otherError("group.Group.clean", e)
                raise

    def __str__(self):
        return self.groupname
