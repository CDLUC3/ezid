# =============================================================================
#
# EZID :: ezidapp/models/link_checker.py
#
# Database model for the link checker's table.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2016, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import hashlib
import re
import time

import django.core.validators
import django.db.models
import ezidapp.models.identifier

import impl.util

_identifierModule = ezidapp.models.identifier


class LinkChecker(django.db.models.Model):
    # Stores all public, real (non-test) identifiers that have
    # non-default target URLs; their target URLs; and link checker
    # results.  This table is updated from the primary EZID tables, but
    # always lags behind; it is not synchronized.

    identifier = django.db.models.CharField(
        max_length=impl.util.maxIdentifierLength, unique=True
    )
    # The identifier in qualified, normalized form, e.g.,
    # "ark:/12345/abc" or "doi:10.1234/ABC".

    owner_id = django.db.models.IntegerField(db_index=True)
    # The identifier's owner.  As this table is populated from the
    # SearchIdentifier table (not ideal, but currently necessary), this
    # field is a foreign key into the SearchUser table.  But it is not
    # expressed as an actual foreign key in order to avoid a hard
    # database dependency.

    # noinspection PyProtectedMember
    target = django.db.models.URLField(
        max_length=_identifierModule.Identifier._meta.get_field("target").max_length
    )
    # The identifier's target URL, e.g., "http://foo.com/bar".

    lastCheckTime = django.db.models.IntegerField(
        default=0, validators=[django.core.validators.MinValueValidator(0)]
    )
    # The time the target URL was last checked as a Unix timestamp.

    @property
    def isVisited(self):
        return self.lastCheckTime > 0

    @property
    def isUnvisited(self):
        return self.lastCheckTime == 0

    numFailures = django.db.models.IntegerField(
        default=0,
        validators=[django.core.validators.MinValueValidator(0)],
        db_index=True,
    )
    # The number of successive check failures.

    isBad = django.db.models.BooleanField(default=False, editable=False)
    # Computed value for indexing purposes.  True if the number of
    # failures is positive.

    @property
    def isGood(self):
        # N.B.: this returns True if the target URL is unvisited.
        return not self.isBad

    returnCode = django.db.models.IntegerField(blank=True, null=True)
    # The HTTP return code from the last check; or a negative value if
    # an I/O error occurred; or None if the target URL hasn't been
    # checked yet.  For link checker purposes, a return code of 200 is
    # synonymous with success.

    error = django.db.models.TextField(blank=True)
    # If returnCode is negative (i.e., if an I/O error occurred), the
    # exception that was encountered; otherwise, empty.

    mimeType = django.db.models.CharField(max_length=255, blank=True)
    # If the last check was successful, the MIME type of the returned
    # resource, e.g., "text/html"; otherwise empty.

    size = django.db.models.IntegerField(
        blank=True, null=True, validators=[django.core.validators.MinValueValidator(0)]
    )
    # If the last check was successful, the size of the returned
    # resource in bytes; otherwise None.

    hash = django.db.models.CharField(max_length=32, blank=True)
    # If the last check was successful, the MD5 hash of the returned
    # resource; otherwise empty.

    class Meta:
        index_together = [("owner_id", "isBad", "lastCheckTime")]

    def clean(self):
        self.isBad = self.numFailures > 0

    def checkSucceeded(self, mimeType, content):
        self.lastCheckTime = int(time.time())
        self.numFailures = 0
        self.returnCode = 200
        self.error = ""
        # Ensure the MIME type is small enough, both with respect to
        # character set and length.
        self.mimeType = re.sub("[^ -~]", "?", mimeType)[
            : self._meta.get_field("mimeType").max_length
        ]
        self.size = len(content)
        self.hash = hashlib.md5(content).hexdigest()

    def checkFailed(self, code, error=None):
        self.lastCheckTime = int(time.time())
        self.numFailures += 1
        self.returnCode = code
        if self.returnCode < 0:
            self.error = error
        self.mimeType = ""
        self.size = None
        self.hash = ""

    def clearHistory(self):
        self.lastCheckTime = 0
        self.numFailures = 0
        self.returnCode = None
        self.error = ""
        self.mimeType = ""
        self.size = None
        self.hash = ""
