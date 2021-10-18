#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Add a new task to each of the async processing queues

Identifier create, update and delete operations are propagated to external services by adding them
to a queue for each service. Each service is handled by a separate async process. The process is
responsible for removing completed operations from its queue.
"""
import logging
import time

import django.apps
import django.conf

import ezidapp.models.async_queue
import ezidapp.models.identifier

log = logging.getLogger(__name__)


def enqueue(
        si_model: ezidapp.models.identifier.Identifier,
        operation_label: str,
) -> None:
    """Add a new create, update or delete operation to each of the async processing queues

    This method should be called within a database transaction that includes the identifier's insert,
    update or delete operation in the Identifier table.

    TODO: Check the situation re. manual transactions. I'm pretty sure we should move to implicit
    transactions managed by Django (which wraps each view call in a transaction).

    REF: update_queue.enqueue()
    """
    si_cls = django.apps.apps.get_model('ezidapp', 'Identifier')
    assert isinstance(si_model, si_cls), f'Unexpected object: {si_model}'
    assert si_model.identifier
    assert operation_label in ("create", "update", "delete")

    # The Identifier we receive may change or be deleted by the time the async processing
    # occurs, so we copy it to a RefIdentifier, which holds the current state of the identifier
    # and is immutable until deleted.

    ref_id_model = create_ref_id_model(si_model)
    _enqueue_all(ref_id_model, operation_label)


def create_ref_id_model(
        id_model: ezidapp.models.identifier.Identifier,
) -> ezidapp.models.identifier.RefIdentifier:
    """Create a RefIdentifier with values from an Identifier

    This captures the current state of an Identifier for later async processing.

    A call to this method always creates and saves a new RefIdentifier. RefIdentifiers may occur any
    number of times for the same identifier, representing the state of the identifier at
    different points in time.

    A RefIdentifier is intended to be immutable until deleted. This is not enforced.

    A RefIdentifier that is not referenced in any queues has been fully processed and can be
    removed.

    'identifier' should be the normalized, qualified identifier, e.g.,
    "doi:10.5060/FOO".

    """
    ref_id_model = ezidapp.models.identifier.RefIdentifier()
    # for field in si_model._meta.fields:
    #     field_value = getattr(si_model, field.name)
    #     setattr(ref_id_model, field.name, field_value)
    log.debug('Creating new RefIdentifier:')
    # noinspection PyProtectedMember
    field_tup = ref_id_model._meta.fields
    # log.debug(f'  fields: {field_tup}')
    for field in field_tup:
        log.debug(f'  {field}')
    for field in field_tup:
        field_value = getattr(id_model, field.name, None)
        setattr(ref_id_model, field.name, field_value)
        log.debug(f'  {field.name} = {field_value}')
    # ref_id_model.computeComputedValues()
    ref_id_model.save()
    return ref_id_model


def _enqueue_all(ref_id_model, operation_label):
    for queue_model in (
        ezidapp.models.async_queue.BinderQueue,
        ezidapp.models.async_queue.CrossrefQueue,
        ezidapp.models.async_queue.DataciteQueue,
        ezidapp.models.async_queue.SearchIndexerQueue,
        # ezidapp.models.async_queue.DownloadQueue,
    ):
        _enqueue_identifier(queue_model, ref_id_model, operation_label)

def _enqueue_identifier(model, ref_id_model, operation_label):
    """Add an identifier to the asynchronous registration queue named by 'model'.

    Args:
        model: Queue model
        ref_id_model: Existing (saved) refIdentifier model
    """
    model(
        # seq='',
        # enqueueTime=datetime.datetime.now().timestamp(),
        enqueueTime=int(time.time()),
        # submitTime='',
        operation=ezidapp.models.async_queue.AsyncQueueBase.OPERATION_LABEL_TO_CODE_DICT[
            operation_label],
        status=ezidapp.models.async_queue.AsyncQueueBase.UNSUBMITTED,
        # message='',
        # batchId='',
        # error='',
        # errorIsPermanent='',
        refIdentifier=ref_id_model,
    ).save()
