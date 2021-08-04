# =============================================================================
#
# EZID :: ezidapp/models/download_queue.py
#
# Database model for the download queue.
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

import impl.util


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
    compression = django.db.models.CharField(
        max_length=1, choices=[(GZIP, "GZIP"), (ZIP, "ZIP")]
    )

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
    lastId = django.db.models.CharField(
        max_length=impl.util.maxIdentifierLength, blank=True
    )

    # The size of the file in bytes after the last flush.  HARVEST stage
    # only.
    fileSize = django.db.models.BigIntegerField(blank=True, null=True)
