# =============================================================================
#
# EZID :: ezidapp/models/registration_queue.py
#
# Abstract database model for external identifier registration queues.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2017, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.db.models

import impl.util


class RegistrationQueue(django.db.models.Model):
    # Describes identifiers awaiting asynchronous registration with an
    # external registrar.  Also, identifiers that previously encountered
    # permanent errors during registration are retained in this table
    # until manually removed.  This class is abstract; there are
    # separate instantiated subclasses of this class for each external
    # registrar.

    class Meta:
        abstract = True

    seq = django.db.models.AutoField(primary_key=True)
    # Order of insertion into this table; also, the order in which
    # identifier operations are to be performed.

    enqueueTime = django.db.models.IntegerField()
    # The time this record was enqueued as a Unix timestamp.

    identifier = django.db.models.CharField(max_length=impl.util.maxIdentifierLength)
    # The identifier in qualified, normalized form, e.g.,
    # "doi:10.5060/FOO".

    metadata = django.db.models.BinaryField()
    # The identifier's metadata dictionary, stored as a gzipped blob.

    CREATE = "C"
    UPDATE = "U"
    DELETE = "D"
    operation = django.db.models.CharField(
        max_length=1,
        choices=[(CREATE, "create"), (UPDATE, "update"), (DELETE, "delete")],
    )
    # The operation to perform.

    _operationMapping = {"create": CREATE, "update": UPDATE, "delete": DELETE}

    @staticmethod
    def operationLabelToCode(label):
        return RegistrationQueue._operationMapping[label]

    error = django.db.models.TextField(blank=True)
    # Any error (transient or permanent) received in processing the
    # identifier.

    errorIsPermanent = django.db.models.BooleanField(default=False)
    # True if the error received is not transient.  Permanent errors
    # disable processing on the identifier and can be removed only
    # manually.
