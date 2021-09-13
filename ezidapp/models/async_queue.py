#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Object Relational Mapper (ORM) models for external identifier registration queues
"""

import django.db.models
import impl.util


class AsyncQueueBase(django.db.models.Model):
    """ORM models for queues of identifier operations awaiting asynchronous registration with an
    external registrar

    Operations are removed from this table by the async process after having been successfully
    submitted.

    Operations that cannot be submitted due to a permanent error must be manually removed.
    """

    class Meta:
        """This model does not itself cause a table to be created. Tables are created by
        subclasses below.
        """
        abstract = True

    @staticmethod
    def operationLabelToCode(label):
        return AsyncQueueBase._operation_dict[label]

    # Order of insertion into this table; also, the order in which
    # identifier operations must be performed.
    seq = django.db.models.AutoField(primary_key=True)

    refIdentifier = django.db.models.ForeignKey(
        to='ezidapp.RefIdentifier',
        on_delete=django.db.models.deletion.PROTECT,
    )

    # The time this record was enqueued as a Unix timestamp.
    # TODO: Change to models.DateTimeField(auto_now_add=True)
    enqueueTime = django.db.models.IntegerField()

    # Once submitted, the time the submission took place as a Unix timestamp.
    # TODO: Change to models.DateTimeField(null=True)
    submitTime = django.db.models.IntegerField(blank=True, null=True)

    # refIdentifier includes the metadata as JSON, so no copy is required here.
    # The identifier's metadata as JSON.
    # metadata = django.db.models.BinaryField()

    # The identifier's owner, referenced by the owner's persistent
    # identifier, e.g., "ark:/99166/p92z12p14".
    # owner = django.db.models.CharField(
    #     max_length=impl.util.maxIdentifierLength,
    #     db_index=True,
    # )

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

    # Any error (transient or permanent) received in processing the
    # identifier.
    error = django.db.models.TextField(blank=True)

    # True if the error received is not transient.  Permanent errors
    # disable processing on the identifier and can be removed only
    # manually.
    errorIsPermanent = django.db.models.BooleanField(default=False)


# Subclasses that create tables from the abstract base model.


class DataciteQueue(AsyncQueueBase):
    pass


class BinderQueue(AsyncQueueBase):
    pass


class CrossrefQueue(AsyncQueueBase):
    pass


# The download queue does not relate to a single identifier, so is implemented separately.


class DownloadQueue(django.db.models.Model):
    # Holds batch download requests.  Since the download processor is
    # single-threaded, if there are multiple entries, only the first
    # entry is "in progress."

    # Order of insertion into this table; also, the order in which
    # requests are processed.
    seq = django.db.models.AutoField(primary_key=True)

    # The time the request was made, as a Unix timestamp.  Not used by
    # EZID, but useful for status monitoring.
    requestTime = django.db.models.IntegerField()

    # The raw request, i.e., the urlencoded query string.
    rawRequest = django.db.models.TextField()

    # The requesting user, referenced by the user's persistent
    # identifier, e.g., "ark:/99166/p92z12p14".
    requestor = django.db.models.CharField(max_length=impl.util.maxIdentifierLength)

    # The download format.
    ANVL = "A"
    CSV = "C"
    XML = "X"
    format = django.db.models.CharField(
        max_length=1, choices=[(ANVL, "ANVL"), (CSV, "CSV"), (XML, "XML")]
    )

    # The compression algorithm.
    GZIP = "G"
    ZIP = "Z"
    compression = django.db.models.CharField(max_length=1, choices=[(GZIP, "GZIP"), (ZIP, "ZIP")])

    # For the CSV format only, a list of the columns to return, e.g.,
    # "LS_id,Serc.what".  Encoded per download.encode.
    columns = django.db.models.TextField(blank=True)

    # A dictionary of zero or more search constraints.  Multiple
    # constraints against a parameter are consolidated into a single
    # constraint against a list of values.  Example:
    # "DStype=LSark%2CSdoi,Spermanence=Stest".  Encoded per
    # download.encode.
    constraints = django.db.models.TextField(blank=True)

    # A dictionary of download options, e.g.,
    # "DSconvertTimestamps=BTrue".  Encoded per download.encode.
    options = django.db.models.TextField(blank=True)

    # A list of zero or more notification email addresses, e.g.,
    # "LSme@this.com,Syou@that.com".  Encoded per download.encode.
    notify = django.db.models.TextField(blank=True)

    # The current processing stage.
    CREATE = "C"
    HARVEST = "H"
    COMPRESS = "Z"
    DELETE = "D"
    MOVE = "M"
    NOTIFY = "N"
    stage = django.db.models.CharField(
        max_length=1,
        choices=[
            (CREATE, "create"),
            (HARVEST, "harvest"),
            (COMPRESS, "compress"),
            (DELETE, "delete"),
            (MOVE, "move"),
            (NOTIFY, "notify"),
        ],
        default=CREATE,
    )

    # The filename root, e.g., "da543b91a0".
    filename = django.db.models.CharField(max_length=10, blank=True)

    # A comma-separated list of persistent identifiers of one or more
    # users to harvest, e.g.,
    # "ark:/99166/p9jm23f63,ark:/99166/p99k45t25".  The list is computed
    # at the time the request is made and not changed thereafter.
    toHarvest = django.db.models.TextField()

    # The index into toHarvest of the user currently being harvested.
    # HARVEST stage only.
    currentIndex = django.db.models.IntegerField(default=0)

    # The last identifier processed.  HARVEST stage only.
    lastId = django.db.models.CharField(max_length=impl.util.maxIdentifierLength, blank=True)

    # The size of the file in bytes after the last flush.  HARVEST stage
    # only.
    fileSize = django.db.models.BigIntegerField(blank=True, null=True)
