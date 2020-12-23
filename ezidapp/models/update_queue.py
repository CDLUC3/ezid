# =============================================================================
#
# EZID :: ezidapp/models/update_queue.py
#
# Database model for the identifier update queue, which is EZID's
# central mechanism for performing and dispatching asynchronous
# identifier processing.  An identifier is inserted into the update
# queue as part of the same transaction that inserts, updates, or
# deletes the identifier in the main StoreIdentifier table.
# Identifiers are removed from the queue by the 'backproc' module
# after they have been processed.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2017, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.core.validators
import django.db.models
import time

from . import custom_fields
from . import store_identifier
import util


class UpdateQueue(django.db.models.Model):
    # Describes identifiers that were created, updated, or deleted, and
    # which are awaiting further, asynchronous processing.

    seq = django.db.models.AutoField(primary_key=True)
    # Order of insertion into this table, and the order in which
    # identifier operations are to be performed.

    enqueueTime = django.db.models.IntegerField(
        blank=True, default="", validators=[django.core.validators.MinValueValidator(0)]
    )
    # The time this record was enqueued as a Unix timestamp.  If not
    # specified, the current time is used.

    identifier = django.db.models.CharField(max_length=util.maxIdentifierLength)
    # The identifier in qualified, normalized form, e.g.,
    # "doi:10.5060/FOO".

    object = custom_fields.StoreIdentifierObjectField()
    # A cached copy of the identifier's StoreIdentifier object.

    @property
    def actualObject(self):
        return self.object[0]

    @property
    def objectBlob(self):
        return self.object[1]

    CREATE = "C"
    UPDATE = "U"
    DELETE = "D"
    operation = django.db.models.CharField(
        max_length=1,
        choices=[(CREATE, "create"), (UPDATE, "update"), (DELETE, "delete")],
    )
    # The operation that caused the identifier to be placed in this table.

    _operationMapping = {"create": CREATE, "update": UPDATE, "delete": DELETE}

    @staticmethod
    def operationLabelToCode(label):
        return UpdateQueue._operationMapping[label]

    updateExternalServices = django.db.models.BooleanField(default=True)
    # If true, external services (DataCite, Crossref) are to be updated.
    # (The N2T binder is also external to EZID, but is always updated.)

    def __unicode__(self):
        return "%s %s" % (self.get_operation_display(), self.identifier)

    def clean(self):
        if self.enqueueTime == "":
            self.enqueueTime = int(time.time())


def enqueue(object, operation, updateExternalServices=True, identifier=None):
    # Enqueues a StoreIdentifier object.  'object' may be a
    # StoreIdentifier object or a blob (see StoreIdentifierObjectField);
    # in the latter case, 'identifier' must be specified.  'operation'
    # is the display form of the operation, i.e., one of the strings
    # "create", "update", or "delete".  This method should be called
    # within a database transaction that includes the identifier's
    # update in the StoreIdentifier table.
    if isinstance(object, store_identifier.StoreIdentifier):
        identifier = object.identifier
    r = UpdateQueue(
        identifier=identifier,
        object=object,
        operation=UpdateQueue.operationLabelToCode(operation),
        updateExternalServices=updateExternalServices,
    )
    r.full_clean()
    r.save()
