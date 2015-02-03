# =============================================================================
#
# EZID :: ezidapp/models.py
#
# Database models.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2014, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.db.models

import util

class CrossrefQueue (django.db.models.Model):
  # Describes identifiers that are either awaiting submission to
  # CrossRef or in the process of being (re-)submitted to CrossRef.
  # (So, reserved identifiers are not included, but test identifiers
  # are.)  Also, identifiers whose submission resulted in a warning or
  # error are retained indefinitely in this table.

  seq = django.db.models.AutoField(primary_key=True)
  # Order of insertion into this table; also, the order in which
  # identifier operations occurred.

  identifier = django.db.models.CharField(
    max_length=util.maximumIdentifierLength, db_index=True)
  # The identifier in qualified, normalized form, e.g.,
  # "doi:10.5060/FOO".  Always a DOI.

  owner = django.db.models.CharField(max_length=util.maximumIdentifierLength,
    db_index=True)
  # The identifier's owner, referenced by the owner's persistent
  # identifier, e.g., "ark:/99166/p92z12p14".

  metadata = django.db.models.BinaryField()
  # The identifier's metadata dictionary, stored as a gzipped blob as
  # in the store database.

  CREATE = "C"
  MODIFY = "M"
  DELETE = "D"
  operation = django.db.models.CharField(max_length=1,
    choices=[(CREATE, "create"), (MODIFY, "modify"), (DELETE, "delete")])
  # The operation that caused the identifier to be placed in this table.

  _operationMapping = {
    "create": CREATE,
    "modify": MODIFY,
    "delete": DELETE }

  @staticmethod
  def operationLabelToCode (label):
    return CrossrefQueue._operationMapping[label]

  UNSUBMITTED = "U"
  SUBMITTED = "S"
  WARNING = "W"
  FAILURE = "F"
  status = django.db.models.CharField(max_length=1,
    choices=[(UNSUBMITTED, "awaiting submission"), (SUBMITTED, "submitted"),
    (WARNING, "registered with warning"), (FAILURE, "registration failed")],
    default=UNSUBMITTED, db_index=True)
  # The status of the submission.

  message = django.db.models.TextField(blank=True)
  # Once submitted and polled at least once, any additional status
  # information as received from CrossRef.  See
  # crossref._pollDepositStatus.

  batchId = django.db.models.CharField(max_length=36, blank=True)
  # Once submitted, the ID of the submission batch.  A UUID, e.g.,
  # "84c91897-5ebe-11e4-b58e-10ddb1cf39e7".  The fictitious filename
  # associated with the submission is the batch ID followed by ".xml".

  submitTime = django.db.models.IntegerField(blank=True, null=True)
  # Once submitted, the time the submission took place as a Unix
  # timestamp.

class DownloadQueue (django.db.models.Model):
  # Holds batch download requests.  Since the download processor is
  # single-threaded, if there are multiple entries, only the first
  # entry is "in progress."

  seq = django.db.models.AutoField(primary_key=True)
  # Order of insertion into this table; also, the order in which
  # requests are processed.

  requestTime = django.db.models.IntegerField()
  # The time the request was made, as a Unix timestamp.  Not used by
  # EZID, but useful for status monitoring.

  requestor = django.db.models.CharField(
    max_length=util.maximumIdentifierLength)
  # The requesting user, referenced by the user's persistent
  # identifier, e.g., "ark:/99166/p92z12p14".

  coOwners = django.db.models.TextField(blank=True)
  # A comma-separated list of zero or more persistent identifiers of
  # users for which the requestor is a co-owner, e.g.,
  # "ark:/99166/p9jm23f63,ark:/99166/p99k45t25".  I.e., if the
  # requestor is R and user U has named R as a co-owner, then U is in
  # the list.  The list is computed at the time the request is made
  # and not changed thereafter.

  ANVL = "A"
  CSV = "C"
  XML = "X"
  format = django.db.models.CharField(max_length=1,
    choices=[(ANVL, "ANVL"), (CSV, "CSV"), (XML, "XML")])
  # The download format.

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
  stage = django.db.models.CharField(max_length=1,
    choices=[(CREATE, "create"), (HARVEST, "harvest"), (COMPRESS, "compress"),
    (DELETE, "delete"), (MOVE, "move"), (NOTIFY, "notify")], default=CREATE)
  # The current processing stage.

  filename = django.db.models.CharField(max_length=10, blank=True)
  # The filename root, e.g., "da543b91a0".

  currentOwner = django.db.models.CharField(
    max_length=util.maximumIdentifierLength, blank=True)
  # The owner currently being harvested (either 'requestor' above or
  # one of the users in 'coOwners').  HARVEST stage only.

  lastId = django.db.models.CharField(max_length=util.maximumIdentifierLength,
    blank=True)
  # The last identifier processed.  HARVEST stage only.

  fileSize = django.db.models.IntegerField(blank=True, null=True)
  # The size of the file in bytes after the last flush.  HARVEST stage
  # only.
