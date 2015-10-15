# =============================================================================
#
# EZID :: ezidapp/models/datacite_queue.py
#
# Database model for the DataCite queue.
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

class DataciteQueue (django.db.models.Model):
  # Describes identifiers awaiting asynchronous DataCite processing.
  # (So, reserved identifiers are not included, but test identifiers
  # are.)  Also, identifiers that encountered permanent errors during
  # processing are retained until manually removed.

  seq = django.db.models.AutoField(primary_key=True)
  # Order of insertion into this table; also, the order in which
  # identifier operations are to be performed.

  enqueueTime = django.db.models.IntegerField()
  # The time this record was enqueued as a Unix timestamp.

  identifier = django.db.models.CharField(
    max_length=util.maximumIdentifierLength)
  # The identifier in qualified, normalized form, e.g.,
  # "doi:10.5060/FOO".  Always a DOI.

  metadata = django.db.models.BinaryField()
  # The identifier's metadata dictionary, stored as a gzipped blob as
  # in the store database.

  OVERWRITE = "O"
  DELETE = "D"
  operation = django.db.models.CharField(max_length=1,
    choices=[(OVERWRITE, "overwrite"), (DELETE, "delete")])
  # The operation to perform.

  _operationMapping = {
    "create": OVERWRITE,
    "modify": OVERWRITE,
    "delete": DELETE }

  @staticmethod
  def operationLabelToCode (label):
    return DataciteQueue._operationMapping[label]

  error = django.db.models.TextField(blank=True)
  # Any error (transient or permanent) received from DataCite in
  # processing the identifier.

  errorIsPermanent = django.db.models.BooleanField(default=False)
  # True if the error received is not transient.  Permanent errors
  # disable processing on the identifier and can be removed only
  # manually (they should never happen in practice).
