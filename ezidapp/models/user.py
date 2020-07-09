# =============================================================================
#
# EZID :: ezidapp/models/user.py
#
# Abstract database model for users.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.core.exceptions
import django.core.validators
import django.db.models
import re

import shoulder
import util
import validation
import nog_minter

# Deferred imports...
"""
import log
import noid_nog
"""


class User(django.db.models.Model):
    # An EZID user, i.e., a login account.

    class Meta:
        abstract = True

    pid = django.db.models.CharField(
        max_length=util.maxIdentifierLength,
        unique=True,
        validators=[validation.agentPid],
    )
    # The user's persistent identifier, e.g., "ark:/99166/bar".  Note
    # that the uniqueness requirement is actually stronger than
    # indicated here: it is expected that all agent (i.e., all user and
    # group) persistent identifiers are unique.

    username = django.db.models.CharField(
        max_length=32,
        unique=True,
        validators=[
            django.core.validators.RegexValidator(
                "^[a-z0-9]+([-_.][a-z0-9]+)*$", "Invalid username.", flags=re.I
            )
        ],
    )
    # The user's username, e.g., "dryad".

    # A note on foreign keys: since the store and search databases are
    # completely separate, foreign keys must reference different target
    # models, and so the declaration of all foreign keys is deferred to
    # the concrete subclasses.  There appears to be no better way to
    # model this in Django.

    # group = django.db.models.ForeignKey(group.Group)
    # The user's group.

    # realm = django.db.models.ForeignKey(realm.Realm)
    # The user's realm.

    def clean(self):
        import log
        import noid_nog

        # The following two statements are here just to support the Django
        # admin app, which has its own rules about how model objects are
        # constructed.  If no group has been assigned, we can return
        # immediately because a validation error will already have been
        # triggered.
        if not hasattr(self, "group"):
            return
        if not hasattr(self, "realm"):
            self.realm = self.group.realm
        if self.realm != self.group.realm:
            raise django.core.exceptions.ValidationError(
                "User's realm does not match user's group's realm."
            )
        if self.pid == "":
            try:
                s = shoulder.getAgentShoulder()
                assert s.isArk, "agent shoulder type must be ARK"
                self.pid = "ark:/" + nog_minter.mint_identifier(s)
            except Exception, e:
                log.otherError("user.User.clean", e)
                raise

    def __unicode__(self):
        return self.username
