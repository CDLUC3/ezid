import impl.util
import logging
import time

import django.conf

import ezidapp.models.registration_queue
import ezidapp.models.registration_queue
import ezidapp.models.registration_queue
import ezidapp.models.registration_queue

log = logging.getLogger(__name__)


def enqueueTask():
    for update_model in update_list:
        if not self._checkContinue():
            break
        # The use of legacy representations and blobs will go away soon.
        metadata = update_model.actualObject.toLegacy()
        blob = impl.util.blobify(metadata)
        if update_model.actualObject.owner is not None:
            try:
                impl.search_util.withAutoReconnect(
                    "searchDb._updateSearchDatabase",
                    lambda: self._updateSearchDatabase(
                        update_model.identifier,
                        update_model.get_operation_display(),
                        metadata,
                        blob,
                    ),
                    self._checkContinue,
                )
            except impl.search_util.AbortException:
                log.exception(' impl.search_util.AbortException')
                break

        with django.db.transaction.atomic():
            if not update_model.actualObject.isReserved:
                impl.daemon.enqueueBinderIdentifier(
                    update_model.identifier,
                    update_model.get_operation_display(),
                    blob,
                )
                if update_model.updateExternalServices:
                    if update_model.actualObject.isDatacite:
                        if not update_model.actualObject.isTest:
                            impl.queue.enqueueDataCiteIdentifier(
                                update_model.identifier,
                                update_model.get_operation_display(),
                                blob,
                            )
                    elif update_model.actualObject.isCrossref:
                        impl.daemon.enqueueCrossrefIdentifier(
                            update_model.identifier,
                            update_model.get_operation_display(),
                            metadata,
                            blob,
                        )
            update_model.delete()

    # else:
    #     django.db.connections["default"].close()
    #     django.db.connections["search"].close()
    #     noinspection PyTypeChecker



def enqueueBinderIdentifier(identifier, operation, blob):
    """Adds an identifier to the binder asynchronous processing queue.

    'identifier' should be the normalized, qualified identifier, e.g.,
    "doi:10.5060/FOO".  'operation' is the identifier operation and
    should be one of the strings "create", "update", or "delete". 'blob'
    is the identifier's metadata dictionary in blob form.
    """
    _enqueueIdentifier(
        ezidapp.models.registration_queue.BinderQueue, identifier, operation, blob
    )


def enqueueCrossrefIdentifier(identifier, operation, metadata, blob):
    """Adds an identifier to the Crossref queue.

    'identifier' should be the normalized, qualified identifier, e.g.,
    "doi:10.5060/FOO". 'operation' is the identifier operation and should
    be one of the strings "create", "update", or "delete".  'metadata' is
    the identifier's metadata dictionary; 'blob' is the same in blob form.
    """
    e = ezidapp.models.registration_queue.CrossrefQueue(
        identifier=identifier,
        owner=metadata["_o"],
        metadata=blob,
        operation=ezidapp.models.registration_queue.CrossrefQueue.operationLabelToCode(
            operation
        ),
    )
    e.save()


def enqueueDataCiteIdentifier(identifier, operation, blob):
    """Adds an identifier to the DataCite asynchronous processing queue.

    'identifier' should be the normalized, qualified identifier, e.g.,
    "doi:10.5060/FOO".  'operation' is the identifier operation and
    should be one of the strings "create", "update", or "delete". 'blob'
    is the identifier's metadata dictionary in blob form.
    """
    _enqueueIdentifier(
        ezidapp.models.registration_queue.DataciteQueue, identifier, operation, blob
    )


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
        operation=ezidapp.models.registration_queue.RegistrationQueue.operationLabelToCode(
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
