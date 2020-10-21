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

import util


class DownloadQueue(django.db.models.Model):
    # Holds batch download requests.  Since the download processor is
    # single-threaded, if there are multiple entries, only the first
    # entry is "in progress."

    seq = django.db.models.AutoField(primary_key=True)
    # Order of insertion into this table; also, the order in which
    # requests are processed.

    requestTime = django.db.models.IntegerField()
    # The time the request was made, as a Unix timestamp.  Not used by
    # EZID, but useful for status monitoring.

    rawRequest = django.db.models.TextField()
    # The raw request, i.e., the urlencoded query string.

    requestor = django.db.models.CharField(max_length=util.maxIdentifierLength)
    # The requesting user, referenced by the user's persistent
    # identifier, e.g., "ark:/99166/p92z12p14".

    ANVL = "A"
    CSV = "C"
    XML = "X"
    format = django.db.models.CharField(
        max_length=1, choices=[(ANVL, "ANVL"), (CSV, "CSV"), (XML, "XML")]
    )
    # The download format.

    GZIP = "G"
    ZIP = "Z"
    compression = django.db.models.CharField(
        max_length=1, choices=[(GZIP, "GZIP"), (ZIP, "ZIP")]
    )
    # The compression algorithm.

    columns = django.db.models.TextField(blank=True)
    # For the CSV format only, a list of the columns to return, e.g.,
    # "LS_id,Serc.what".  Encoded per download._encode.

    constraints = django.db.models.TextField(blank=True)
    # A dictionary of zero or more search constraints.  Multiple
    # constraints against a parameter are consolidated into a single
    # constraint against a list of values.  Example:
    # "DStype=LSark%2CSdoi,Spermanence=Stest".  Encoded per
    # download._encode.

    options = django.db.models.TextField(blank=True)
    # A dictionary of download options, e.g.,
    # "DSconvertTimestamps=BTrue".  Encoded per download._encode.

    notify = django.db.models.TextField(blank=True)
    # A list of zero or more notification email addresses, e.g.,
    # "LSme@this.com,Syou@that.com".  Encoded per download._encode.

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
    # The current processing stage.

    filename = django.db.models.CharField(max_length=10, blank=True)
    # The filename root, e.g., "da543b91a0".

    toHarvest = django.db.models.TextField()
    # A comma-separated list of persistent identifiers of one or more
    # users to harvest, e.g.,
    # "ark:/99166/p9jm23f63,ark:/99166/p99k45t25".  The list is computed
    # at the time the request is made and not changed thereafter.

    currentIndex = django.db.models.IntegerField(default=0)
    # The index into toHarvest of the user currently being harvested.
    # HARVEST stage only.

    lastId = django.db.models.CharField(max_length=util.maxIdentifierLength, blank=True)
    # The last identifier processed.  HARVEST stage only.

    fileSize = django.db.models.BigIntegerField(blank=True, null=True)
    # The size of the file in bytes after the last flush.  HARVEST stage
    # only.
