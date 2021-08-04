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

import ezidapp.models.custom_fields
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

    # Order of insertion into this table; also, the order in which
    # identifier operations are to be performed.
    seq = django.db.models.AutoField(primary_key=True)

    # The time this record was enqueued as a Unix timestamp.
    enqueueTime = django.db.models.IntegerField()

    # The identifier in qualified, normalized form, e.g.,
    # "doi:10.5060/FOO".
    identifier = django.db.models.CharField(max_length=impl.util.maxIdentifierLength)

    # The identifier's metadata dictionary, stored as a gzipped blob.
    # In old EZID, 'metadata' in the queues is a regular BinaryField, so serialization and
    # deserialization between Python object and compressed blob had to be done manually whenever
    # this field was read and written.
    metadata = django.db.models.BinaryField()
    # metadata = ezidapp.models.custom_fields.CompressedJsonField()

    # The operation to perform.
    CREATE = "C"
    UPDATE = "U"
    DELETE = "D"
    operation = django.db.models.CharField(
        max_length=1,
        choices=[(CREATE, "create"), (UPDATE, "update"), (DELETE, "delete")],
    )
    _operationMapping = {"create": CREATE, "update": UPDATE, "delete": DELETE}

    @staticmethod
    def operationLabelToCode(label):
        return RegistrationQueue._operationMapping[label]

    # Any error (transient or permanent) received in processing the
    # identifier.
    error = django.db.models.TextField(blank=True)

    # True if the error received is not transient.  Permanent errors
    # disable processing on the identifier and can be removed only
    # manually.
    errorIsPermanent = django.db.models.BooleanField(default=False)
