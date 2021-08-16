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
    """Abstract queue of identifier operations awaiting asynchronous registration with an
    external registrar.

    Operations are removed from this table by the async process after having been successfully
    submitted.

    Operations that cannot be submitted due to a permanent error must be manually removed.
    """

    class Meta:
        abstract = True

    # Order of insertion into this table; also, the order in which
    # identifier operations must be performed.
    seq = django.db.models.AutoField(primary_key=True)

    # The time this record was enqueued as a Unix timestamp.
    enqueueTime = django.db.models.IntegerField()

    # Once submitted, the time the submission took place as a Unix timestamp.
    submitTime = django.db.models.IntegerField(blank=True, null=True)

    # The identifier in qualified, normalized form, e.g., "doi:10.5060/FOO".
    identifier = django.db.models.CharField(max_length=impl.util.maxIdentifierLength, db_index=True)

    # The identifier's metadata as JSON.
    metadata = django.db.models.BinaryField()

    # The identifier's owner, referenced by the owner's persistent
    # identifier, e.g., "ark:/99166/p92z12p14".
    owner = django.db.models.CharField(
        max_length=impl.util.maxIdentifierLength,
        db_index=True,
    )

    # The operation which is to be registered.
    CREATE = "C"
    UPDATE = "U"
    DELETE = "D"

    _operation_dict = {
        "create": CREATE,
        "update": UPDATE,
        "delete": DELETE,
    }

    operation = django.db.models.CharField(
        max_length=1,
        choices=[
            (CREATE, "create"),
            (UPDATE, "update"),
            (DELETE, "delete"),
        ],
    )

    # The status of the submission.

    UNSUBMITTED = "U"
    SUBMITTED = "S"
    WARNING = "W"
    FAILURE = "F"

    _status_dict = {
        UNSUBMITTED: 'Unsubmitted',
        SUBMITTED: 'Submitted',
        WARNING: 'Warning',
        FAILURE: 'Failure',

    }

    status = django.db.models.CharField(
        max_length=1,
        choices=[
            (UNSUBMITTED, "awaiting submission"),
            (SUBMITTED, "submitted"),
            (WARNING, "registered with warning"),
            (FAILURE, "registration failed"),
        ],
        default=UNSUBMITTED,
        db_index=True,
    )

    # Once submitted and polled at least once, any additional status
    # information as received from Crossref.  See
    # crossref._pollDepositStatus.
    message = django.db.models.TextField(blank=True)

    # Once submitted, the ID of the submission batch.  A UUID, e.g.,
    # "84c91897-5ebe-11e4-b58e-10ddb1cf39e7".  The fictitious filename
    # associated with the submission is the batch ID followed by ".xml".
    batchId = django.db.models.CharField(max_length=36, blank=True)

    @staticmethod
    def operationLabelToCode(label):
        return RegistrationQueue._operation_dict[label]

    # Any error (transient or permanent) received in processing the
    # identifier.
    error = django.db.models.TextField(blank=True)

    # True if the error received is not transient.  Permanent errors
    # disable processing on the identifier and can be removed only
    # manually.
    errorIsPermanent = django.db.models.BooleanField(default=False)


class DataciteQueue(RegistrationQueue):
    pass


class BinderQueue(RegistrationQueue):
    pass


class CrossrefQueue(RegistrationQueue):
    pass
