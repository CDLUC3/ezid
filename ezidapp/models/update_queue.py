# =============================================================================
#
# EZID :: ezidapp/models/update_queue.py
#
# Database model for the identifier update queue, which is EZID's
# central mechanism for performing and dispatching asynchronous
# identifier processing.  An identifier is inserted into the update
# queue as part of the same transaction that inserts, updates, or
# deletes the identifier in the main StoreIdentifier table.
# Identifiers are removed from the queue by the SearchDbDaemon
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

import django.apps
import time

import django.core.validators
import django.db.models

import ezidapp.models.identifier
import ezidapp.models.custom_fields
import impl.util

CREATE = "C"
UPDATE = "U"
DELETE = "D"
OPERATION_DICT = {"create": CREATE, "update": UPDATE, "delete": DELETE}


class UpdateQueue(django.db.models.Model):
    """Storage for identifiers that were created, updated, or deleted, and
    which are awaiting further, asynchronous processing.
    """

    # Order of insertion into this table, and the order in which
    # identifier operations are to be performed.
    seq = django.db.models.AutoField(primary_key=True)

    # The time this record was enqueued as a Unix timestamp.  If not
    # specified, the current time is used.
    enqueueTime = django.db.models.IntegerField(
        blank=True, default="", validators=[django.core.validators.MinValueValidator(0)]
    )

    # The identifier in qualified, normalized form, e.g.,
    # "doi:10.5060/FOO".
    identifier = django.db.models.CharField(max_length=impl.util.maxIdentifierLength)

    # # A cached copy of the identifier's StoreIdentifier object.
    # object = ezidapp.models.custom_fields.StoreIdentifierObjectField()

    # ref_identifier_model = django.apps.apps.get_model('ezidapp', 'RefIdentifier')

    object = django.db.models.ForeignKey(
        # TODO: Check if PROTECT is the on_delete policy we need here.
        'ezidapp.RefIdentifier', on_delete=django.db.models.PROTECT,
        # null=True,
    )

    @property
    def actualObject(self):
        return self.object[0]

    @property
    def objectBlob(self):
        return self.object[1]

    operation = django.db.models.CharField(
        max_length=1,
        choices=[(CREATE, "create"), (UPDATE, "update"), (DELETE, "delete")],
    )

    @staticmethod
    def operationLabelToCode(label):
        return OPERATION_DICT[label]

    # If true, external services (DataCite, Crossref) are to be updated.
    # (The N2T binder is also external to EZID, but is always updated.)
    updateExternalServices = django.db.models.BooleanField(default=True)

    def __str__(self):
        return f"{self.get_operation_display()} {self.identifier}"

    def clean(self):
        if self.enqueueTime == "":
            self.enqueueTime = int(time.time())


def enqueue(refIdentifier, operation, updateExternalServices=True):
    # Enqueues a StoreIdentifier object.  'object' may be a
    # StoreIdentifier object or a blob (see StoreIdentifierObjectField);
    # in the latter case, 'identifier' must be specified.  'operation'
    # is the display form of the operation, i.e., one of the strings
    # "create", "update", or "delete".  This method should be called
    # within a database transaction that includes the identifier's
    # update in the StoreIdentifier table.

    # si:ezidapp.models.identifier.Identifier = storeIdentifier
    ri:ezidapp.models.identifier.RefIdentifier = refIdentifier

    assert isinstance(ri, ezidapp.models.identifier.Identifier)

    ri.pk = None
    ri.save()

    # store_identifier_model = django.apps.apps.get_model('ezidapp', 'StoreIdentifier')
    # if isinstance(refIdentifier, store_identifier_model):
    #     identifier = refIdentifier.identifier
    r = UpdateQueue(
        identifier=ri.identifier, #.encode('utf-8'),
        object=ri,
        operation=UpdateQueue.operationLabelToCode(operation),
        updateExternalServices=updateExternalServices,
    )
    r.full_clean()
    r.save()

# def enqueue(object, operation, updateExternalServices=True, identifier=None):
#     # Enqueues a StoreIdentifier object.  'object' may be a
#     # StoreIdentifier object or a blob (see StoreIdentifierObjectField);
#     # in the latter case, 'identifier' must be specified.  'operation'
#     # is the display form of the operation, i.e., one of the strings
#     # "create", "update", or "delete".  This method should be called
#     # within a database transaction that includes the identifier's
#     # update in the StoreIdentifier table.
#     store_identifier_model = django.apps.apps.get_model('ezidapp', 'StoreIdentifier')
#     if isinstance(object, store_identifier_model):
#         identifier = object.identifier
#     r = UpdateQueue(
#         identifier=identifier.encode('utf-8'),
#         object=object,
#         operation=UpdateQueue.operationLabelToCode(operation),
#         updateExternalServices=updateExternalServices,
#     )
#     r.full_clean()
#     r.save()
