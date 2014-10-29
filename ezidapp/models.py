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

class CrossrefQueue (django.db.models.Model):
  # Describes identifiers that are either awaiting submission to
  # CrossRef or in the process of being (re-)submitted to CrossRef.
  # (So, reserved identifiers are not included, but test identifiers
  # are.)  Also, identifiers whose submission resulted in a warning or
  # error are retained indefinitely in this table.

  seq = django.db.models.AutoField(primary_key=True)
  # Order of insertion into this table; also, the order in which
  # identifier operations occurred.

  identifier = django.db.models.CharField(max_length=256, db_index=True)
  # The identifier in qualified, normalized form, e.g.,
  # "doi:10.5060/FOO".  Always a DOI.

  owner = django.db.models.CharField(max_length=256, db_index=True)
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
  UNKNOWN = "?"
  status = django.db.models.CharField(max_length=1,
    choices=[(UNSUBMITTED, "awaiting submission"), (SUBMITTED, "submitted"),
    (WARNING, "registered with warning"), (FAILURE, "registration failed"),
    (UNKNOWN, "unknown")], default=UNSUBMITTED, db_index=True)
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
