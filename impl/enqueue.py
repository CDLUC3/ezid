#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Add a new task to each of the async processing queues

Identifier create, update and delete operations are propagated to external services by adding them
to a queue for each service. Each service is handled by a separate async process. The process is
responsible for removing completed operations from its queue.
"""
import ezidapp.models.identifier
import impl.util
import logging
import time

import django.conf

import ezidapp.models.async_queue

log = logging.getLogger(__name__)


def enqueue(
    si_model: ezidapp.models.identifier.Identifier,
    operation: str,
) -> None:
    """Add a new create, update or delete operation to each of the async processing queues

    This method should be called within a database transaction that includes the identifier's insert,
    update or delete operation in the Identifier table.

    TODO: Check the situation re. manual transactions. I'm pretty sure we should move to implicit
    transactions managed by Django (which wraps each view call in a transaction).

    REF: update_queue.enqueue()
    """
    si_cls = django.apps.apps.get_model('ezidapp', 'Identifier')
    assert isinstance(si_model, si_cls)
    assert si_model.identifier
    assert operation in ("create", "update", "delete")

    # The Identifier we receive may change or be deleted by the time the async processing
    # occurs, so we copy it to a RefIdentifier, which holds the current state of the identifier
    # and is immutable until deleted.

    ri_model = create_ref_identifier(si_model)

    r = ezidapp.models.async_queue.AsyncQueue(
        # seq = '',
        refIdentifier = ri_model,
        # enqueueTime = '',
        # submitTime = '',
        operation = ezidapp.models.async_queue.AsyncQueue.operationLabelToCode(operation),
        # status = '',
        # message = '',
        # batchId = '',
        # error = '',
        # errorIsPermanent = '',
        ## owner = '',
    )

    r.full_clean()
    r.save()


def create_ref_identifier(
    si_model: ezidapp.models.identifier.Identifier,
) -> ezidapp.models.identifier.RefIdentifier:
    """Create a RefIdentifier with values from a Identifier

    This captures the current state of a Identifier for later async processing.

    A call to this method always creates and saves a new RefIdentifier. RefIdentifiers may occur any
    number of times for the same identifier, representing different states of the identifier.

    A RefIdentifier that is not referenced in any queues has been fully processed and can be
    removed.
    """
    ri_model = ezidapp.models.identifier.RefIdentifier()
    # noinspection PyProtectedMember
    for field in si_model._meta.fields:
        field_value = getattr(si_model, field.name)
        setattr(ri_model, field.name, field_value)
    log.debug(f'Created new RefIdentifier: "{ri_model}"')
    ri_model.save()
    return ri_model


# metadata = update_model.actualObject.toLegacy()
# blob = impl.util.blobify(metadata)
# if update_model.actualObject.owner is not None:
#     try:
#             lambda: self._updateSearchDatabase(
#                 update_model.identifier,
#                 update_model.get_operation_display(),
#                 metadata,
#                 blob,
#             ),
#             self._checkContinue,
#         )
#     except impl.search_util.AbortException:
#         log.exception(' impl.search_util.AbortException')
#         break
#
# with django.db.transaction.atomic():
#     if not update_model.actualObject.isReserved:
#         enqueueBinderIdentifier(
#             update_model.identifier,
#             update_model.get_operation_display(),
#             blob,
#         )
#         if update_model.updateExternalServices:
#             if update_model.actualObject.isDatacite:
#                 if not update_model.actualObject.isTest:
#                     enqueueDataCiteIdentifier(
#                         update_model.identifier,
#                         update_model.get_operation_display(),
#                         blob,
#                     )
#             elif update_model.actualObject.isCrossref:
#                 enqueueCrossrefIdentifier(
#                     update_model.identifier,
#                     update_model.get_operation_display(),
#                     metadata,
#                     blob,
#                 )
#     update_model.delete()
#
# # else:
# #     django.db.connections["default"].close()
# #     django.db.connections["search"].close()
# #     noinspection PyTypeChecker


def enqueueBinderIdentifier(identifier, operation, blob):
    """Adds an identifier to the binder asynchronous processing queue

    'identifier' should be the normalized, qualified identifier, e.g.,
    "doi:10.5060/FOO".  'operation' is the identifier operation and
    should be one of the strings "create", "update", or "delete". 'blob'
    is the identifier's metadata dictionary in blob form.
    """
    _enqueueIdentifier(ezidapp.models.async_queue.BinderQueue, identifier, operation, blob)


def enqueueCrossrefIdentifier(identifier, operation, metadata, blob):
    """Adds an identifier to the Crossref queue

    'identifier' should be the normalized, qualified identifier, e.g.,
    "doi:10.5060/FOO". 'operation' is the identifier operation and should
    be one of the strings "create", "update", or "delete".  'metadata' is
    the identifier's metadata dictionary; 'blob' is the same in blob form.
    """
    e = ezidapp.models.async_queue.CrossrefQueue(
        identifier=identifier,
        owner=metadata["_o"],
        metadata=blob,
        operation=ezidapp.models.async_queue.CrossrefQueue.operationLabelToCode(operation),
    )
    e.save()


def enqueueDataCiteIdentifier(identifier, operation, blob):
    """Adds an identifier to the DataCite asynchronous processing queue

    'identifier' should be the normalized, qualified identifier, e.g.,
    "doi:10.5060/FOO".  'operation' is the identifier operation and
    should be one of the strings "create", "update", or "delete". 'blob'
    is the identifier's metadata dictionary in blob form.
    """
    _enqueueIdentifier(ezidapp.models.async_queue.DataciteQueue, identifier, operation, blob)


def _enqueueIdentifier(model, identifier, operation, blob):
    """Adds an identifier to the asynchronous registration queue named by
    'model'.

    'identifier' should be the normalized, qualified identifier, e.g.,
    "doi:10.5060/FOO".  'operation' is the identifier operation and
    should be one of the strings "create", "update", or "delete".
    'blob' is the identifier's metadata dictionary in blob form.
    """
    e = model(
        enqueueTime=int(time.time()),
        identifier=identifier,
        metadata=blob,
        operation=ezidapp.models.async_queue.AsyncQueue.operationLabelToCode(
            operation
        ),
    )
    e.save()


def is_daemon_enabled(setting_name):
    assert isinstance(
        setting_name, str
    ), 'Call with the name of a DAEMONS_*_ENABLED setting, not the value.'
    if not django.conf.settings.DAEMONS_ENABLED:
        return False
    v = getattr(django.conf.settings, setting_name, None)
    assert v is not None, f'Unknown setting: {setting_name}'
    assert v in (
        True,
        False,
    ), f'Setting must be a boolean, not {type(setting_name)}'
    return v
