#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Database model for the link checker's table
"""

import hashlib
import re
import time

import django.core.validators
import django.db.models

import ezidapp.models.identifier
import impl.util


class LinkChecker(django.db.models.Model):
    def __str__(self):
        return (
            f'{self.__class__.__name__}('
            f'pk={self.pk}, '
            f'id={self.identifier}, '
            f'error={self.error}, '
            f'numFailures={self.numFailures}, '
            f'size={self.size}, '
            f'target={self.target}'
            f')'
        )

    class Meta:
        indexes = [django.db.models.Index(fields=["owner_id", "isBad", "lastCheckTime"])]

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

    # Stores all public, real (non-test) identifiers that have
    # non-default target URLs; their target URLs; and link checker
    # results. This table is updated from the primary EZID tables, but
    # always lags behind; it is not synchronized.

    # The identifier in qualified, normalized form, e.g.,
    # "ark:/12345/abc" or "doi:10.1234/ABC".
    identifier = django.db.models.CharField(max_length=impl.util.maxIdentifierLength, unique=True)

    # The identifier's owner. As this table is populated from the
    # Identifier table (not ideal, but currently necessary), this
    # field is a foreign key into the User table. But it is not
    # expressed as an actual foreign key in order to avoid a hard
    # database dependency.
    owner_id = django.db.models.IntegerField(db_index=True)

    # id_model = django.apps.apps.get_model('ezidapp', 'Identifier')
    # max_length=id_model.meta.get_field("target").max_length,
    # noinspection PyProtectedMember
    target = django.db.models.URLField(
        max_length=2000,
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

    # The number of successive check failures.
    numFailures = django.db.models.IntegerField(
        default=0,
        validators=[django.core.validators.MinValueValidator(0)],
        db_index=True,
    )

    # Computed value for indexing purposes. True if the number of
    # failures is positive.
    isBad = django.db.models.BooleanField(default=False, editable=False)

    @property
    def isGood(self):
        # N.B.: this returns True if the target URL is unvisited.
        return not self.isBad

    # The HTTP return code from the last check; or a negative value if
    # an I/O error occurred; or None if the target URL hasn't been
    # checked yet. For link checker purposes, a return code of 200 is
    # synonymous with success.
    returnCode = django.db.models.IntegerField(blank=True, null=True)

    # If returnCode is negative (i.e., if an I/O error occurred), the
    # exception that was encountered; otherwise, empty.
    error = django.db.models.TextField(blank=True)

    # If the last check was successful, the MIME type of the returned
    # resource, e.g., "text/html"; otherwise empty.
    mimeType = django.db.models.CharField(max_length=255, blank=True)

    # If the last check was successful, the size of the returned
    # resource in bytes; otherwise None.
    size = django.db.models.IntegerField(
        blank=True, null=True, validators=[django.core.validators.MinValueValidator(0)]
    )

    # If the last check was successful, the MD5 hash of the returned
    # resource; otherwise empty.
    hash = django.db.models.CharField(max_length=32, blank=True)
