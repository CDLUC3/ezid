#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Simple locking mechanism to ensure that, in a multi-threaded environment, no given
identifier is operated on by two threads simultaneously. Additionally, we enforce a
per-user throttle on concurrent operations. _activeUsers maps local usernames to the
number of operations currently being performed by that user. For status reporting
purposes, _waitingUsers similarly maps local usernames to numbers of waiting requests.
If _paused is true, no new locks are granted, but the mechanism otherwise operates
normally.
"""

import logging
import sys
import threading
import uuid

import django.conf
import django.core.exceptions
import django.conf
import django.db.transaction
import django.db.utils

import ezidapp.models.identifier
import ezidapp.models.model_util
import ezidapp.models.shoulder
import ezidapp.models.user
import ezidapp.models.util
import impl.enqueue
import impl.log
import impl.nog_sql.ezid_minter
import impl.policy
import impl.util
import impl.util2

logger = logging.getLogger(__name__)

_lockedIdentifiers = set()
_activeUsers = {}
_waitingUsers = {}
_lock = threading.Condition()
_paused = False


def _incrementCount(d, k):
    d[k] = d.get(k, 0) + 1


def _decrementCount(d, k):
    if d[k] == 1:
        del d[k]
    else:
        d[k] -= 1


def _acquireIdentifierLock(identifier, user):
    _lock.acquire()
    # noinspection PyTypeChecker
    while (
        _paused
        or identifier in _lockedIdentifiers
        or _activeUsers.get(user, 0) >= django.conf.settings.MAX_CONCURRENT_OPERATIONS_PER_USER
    ):
        # noinspection PyTypeChecker
        if _activeUsers.get(user, 0) + _waitingUsers.get(user, 0) >= int(
            django.conf.settings.MAX_THREADS_PER_USER
        ):
            _lock.release()
            return False
        _incrementCount(_waitingUsers, user)
        _lock.wait()
        _decrementCount(_waitingUsers, user)
    _incrementCount(_activeUsers, user)
    _lockedIdentifiers.add(identifier)
    _lock.release()
    return True


def _releaseIdentifierLock(identifier, user):
    _lock.acquire()
    _lockedIdentifiers.remove(identifier)
    _decrementCount(_activeUsers, user)
    _lock.notifyAll()
    _lock.release()


def getStatus():
    """Return a tuple consisting of two dictionaries and a boolean flag

    The first dictionary maps local usernames to the number of
    operations currently being performed by that user; the sum of the
    dictionary values is the total number of operations currently being
    performed. The second dictionary similarly maps local usernames to
    numbers of waiting requests. The boolean flag indicates if the
    server is currently paused.
    """
    _lock.acquire()
    try:
        return _activeUsers.copy(), _waitingUsers.copy(), _paused
    finally:
        _lock.release()


def pause(newValue):
    """Set or unsets the paused flag and returns the flag's previous value

    If the server is paused, no new identifier locks are granted and all
    requests are forced to wait.
    """
    global _paused
    _lock.acquire()
    try:
        oldValue = _paused
        _paused = newValue
        if not _paused:
            _lock.notifyAll()
        return oldValue
    finally:
        _lock.release()


# noinspection PyDefaultArgument
def mintIdentifier(shoulder, user, metadata={}):
    if not _acquireIdentifierLock(shoulder + '.shoulder_lock', user.username + '.shoulder_lock'):
        return "error: concurrency limit exceeded"
    try:
        return _mintIdentifier(shoulder, user, metadata)
    finally:
        _releaseIdentifierLock(shoulder + '.shoulder_lock', user.username + '.shoulder_lock')


# noinspection PyDefaultArgument
def _mintIdentifier(shoulder, user, metadata={}):
    """Mint an identifier under the given qualified shoulder, e.g.,
    "doi:10.5060/". 'user' is the requestor and should be an authenticated
    User object. 'metadata' should be a dictionary of element (name,
    value) pairs. If an initial target URL is not supplied, the identifier is
    given a self-referential target URL. The successful return is a string that
    includes the canonical, qualified form of the new identifier, as in:

      success: ark:/95060/fk35717n0h

    For DOI identifiers, the string also includes the qualified shadow
    ARK, as in:

      success: doi:10.5060/FK35717N0H | ark:/b5060/fk35717n0h

    Unsuccessful returns include the strings:

      error: forbidden
      error: bad request - subreason...
      error: internal server error
      error: concurrency limit exceeded
    """
    tid = uuid.uuid1()

    # TODO: We want to be able to support rendering error messages to end users in
    # production like current version of EZID does without breaking rendering of
    # Django's exception diagnostics page in debug mode and without
    # having to wrap large sections of code in exception handlers just for redirecting
    # to a logger.

    impl.log.begin(
        tid,
        "mintIdentifier",
        shoulder,
        user.username,
        user.pid,
        user.group.groupname,
        user.group.pid,
    )

    shoulder_model = ezidapp.models.shoulder.getShoulder(shoulder)

    if shoulder_model is None:
        impl.log.badRequest(tid)
        # TODO: Errors should be raised, not returned.
        return "error: bad request - no such shoulder"

    if shoulder_model.isUuid:
        identifier = "uuid:" + str(uuid.uuid1())
    else:
        if shoulder_model.minter == "":
            impl.log.badRequest(tid)
            return "error: bad request - shoulder does not support minting"

        identifier = impl.nog_sql.ezid_minter.mint_id(shoulder_model)
        if identifier:
            logger.debug('Minter returned identifier: {}'.format(identifier))
        else:
            return f"error: minter failed to create an identifier on shoulder {shoulder_model}"

        # proto super shoulder check
        prefix_val = django.conf.settings.PROTO_SUPER_SHOULDER.get(shoulder_model.prefix, shoulder_model.prefix)

        if shoulder_model.prefix.startswith('doi:'):
            identifier = prefix_val + identifier.upper()
        elif shoulder_model.prefix.startswith('ark:/'):
            identifier = prefix_val + identifier.lower()
        else:
            raise ValueError('Expected ARK or DOI prefix, not "{}"'.format(shoulder_model.prefix))

        logger.debug('Final shoulder + identifier: {}'.format(identifier))

    assert not ezidapp.models.identifier.Identifier.objects.filter(
        identifier=identifier
    ).exists(), (
        f'Freshly minted identifier already exists in the database. '
        f'The minter state for the shoulder may be outdated. '
        f'shoulder="{shoulder_model.prefix}", identifier="{identifier}"'
    )

    impl.log.success(tid, identifier)

    return createIdentifier(identifier, user, metadata)


def createIdentifier(identifier, user, metadata=None, updateIfExists=False):
    """Create an identifier having the given qualified name, e.g.,
    "doi:10.5060/FOO". 'user' is the requestor and should be an authenticated
    User object. 'metadata' should be a dictionary of element (name,
    value) pairs. If an initial target URL is not supplied, the identifier is
    given a self-referential target URL. The successful return is a string that
    includes the canonical, qualified form of the new identifier, as in:

      success: ark:/95060/foo

    For DOI identifiers, the string also includes the qualified shadow
    ARK, as in:

      success: doi:10.5060/FOO | ark:/b5060/foo

    Unsuccessful returns include the strings:

      error: forbidden
      error: bad request - subreason...
      error: internal server error
      error: concurrency limit exceeded

    If 'updateIfExists' is true, an "identifier already exists" error
    falls through to a 'setMetadata' call.
    """
    if metadata is None:
        metadata = {}
    normalizedIdentifier = impl.util.normalizeIdentifier(identifier)
    if normalizedIdentifier is None:
        return "error: bad request - invalid identifier"
    tid = uuid.uuid1()
    if not _acquireIdentifierLock(normalizedIdentifier, user.username):
        return "error: concurrency limit exceeded"
    try:
        impl.log.begin(
            tid,
            "createIdentifier",
            f'normalizedIdentifier="{normalizedIdentifier}"',
            f'user.username="{user.username}"',
            f'user.pid="{user.pid}"',
            f'user.group.groupname="{user.group.groupname}"',
            f'user.group.pid="{user.group.pid}"',
            f'metadata="{",".join(f"{k}={v}" for k, v in metadata.items())}"',
        )
        if not impl.policy.authorizeCreate(user, normalizedIdentifier):
            impl.log.forbidden(tid)
            return "error: forbidden"

        si = ezidapp.models.identifier.Identifier(
            identifier=normalizedIdentifier,
            owner=(None if user == ezidapp.models.user.AnonymousUser else user),
        )
        si.updateFromUntrustedLegacy(metadata, allowRestrictedSettings=user.isSuperuser)
        if si.isDoi:
            s = ezidapp.models.shoulder.getLongestShoulderMatch(si.identifier)
            # Should never happen.
            assert s is not None, "no matching shoulder found"
            if s.isDatacite:
                if si.datacenter is None:
                    si.datacenter = s.datacenter
            elif s.isCrossref:
                if not si.isCrossref:
                    if si.isReserved:
                        si.crossrefStatus = ezidapp.models.identifier.Identifier.CR_RESERVED
                    else:
                        si.crossrefStatus = ezidapp.models.identifier.Identifier.CR_WORKING
            else:
                assert False, "unhandled case"
        si.my_full_clean()
        if si.owner != user:
            if not impl.policy.authorizeOwnershipChange(user, user, si.owner):
                impl.log.badRequest(tid)
                return "error: bad request - ownership change prohibited"

        with django.db.transaction.atomic():
            si.save()
            impl.enqueue.enqueue(si, "create", updateExternalServices=True)

    except django.core.exceptions.ValidationError as e:
        impl.log.badRequest(tid)
        return "error: bad request - " + impl.util.formatValidationError(e)
    except django.db.utils.IntegrityError as e:
        if updateIfExists:
            logger.info(f"create or update with update_if_exists=yes; identifier already exists, update; identifier={identifier}")
            return setMetadata(identifier, user, metadata, internalCall=True)
        else:
            logger.error(str(e))
            impl.log.badRequest(tid)
            return "error: bad request - identifier already exists, cannot create"
    except Exception as e:
        impl.log.error(tid, e)
        if hasattr(sys, 'is_running_under_pytest'):
            raise
        return "error: internal server error"
    else:
        impl.log.success(tid)
        if si.isDoi:
            return f"success: {normalizedIdentifier} | {si.arkAlias}"
        else:
            return "success: " + normalizedIdentifier
    finally:
        _releaseIdentifierLock(normalizedIdentifier, user.username)


def getMetadata(identifier, user=ezidapp.models.user.AnonymousUser, prefixMatch=False):
    """Return all metadata for a given qualified identifier, e.g.,
    "doi:10.5060/FOO". 'user' is the requestor and should be an authenticated
    User object. The successful return is a pair (status, dictionary)
    where 'status' is a string that includes the canonical, qualified form of
    the identifier, as in:

      success: doi:10.5060/FOO

    and 'dictionary' contains element (name, value) pairs. Unsuccessful
    returns include the strings:

      error: forbidden
      error: bad request - subreason...
      error: internal server error
      error: concurrency limit exceeded

    If 'prefixMatch' is true, prefix matching is enabled and the
    returned identifier is the longest identifier that matches a
    (possibly proper) prefix of the requested identifier. In such a
    case, the status string resembles:

      success: doi:10.5060/FOO in_lieu_of doi:10.5060/FOOBAR
    """
    nqidentifier = impl.util.normalizeIdentifier(identifier)
    if nqidentifier is None:
        return "error: bad request - invalid identifier"
    tid = uuid.uuid1()
    if not _acquireIdentifierLock(nqidentifier, user.username):
        return "error: concurrency limit exceeded"
    try:
        impl.log.begin(
            tid,
            "getMetadata",
            nqidentifier,
            user.username,
            user.pid,
            user.group.groupname,
            user.group.pid,
            str(prefixMatch),
        )
        si = ezidapp.models.identifier.getIdentifier(nqidentifier, prefixMatch)
        if not impl.policy.authorizeView(user, si):
            impl.log.forbidden(tid)
            return "error: forbidden"
        d = si.toLegacy()
        ezidapp.models.model_util.convertLegacyToExternal(d)
        if si.isDoi:
            d["_shadowedby"] = si.arkAlias
        impl.log.success(tid)
        if prefixMatch and si.identifier != nqidentifier:
            return f"success: {si.identifier} in_lieu_of {nqidentifier}", d
        else:
            return "success: " + nqidentifier, d
    except ezidapp.models.identifier.Identifier.DoesNotExist:
        impl.log.badRequest(tid)
        return "error: bad request - no such identifier"
    except Exception as e:
        impl.log.error(tid, e)
        if hasattr(sys, 'is_running_under_pytest'):
            raise
        return "error: internal server error"
    finally:
        _releaseIdentifierLock(nqidentifier, user.username)


def setMetadata(identifier, user, metadata, updateExternalServices=True, internalCall=False):
    """Set metadata elements of a given qualified identifier, e.g., "doi:10.5060/FOO".

    'user' is the requestor and should be an authenticated User object. 'metadata'
    should be a dictionary of element (name, value) pairs. If an element being set
    already exists, it is overwritten, if not, it is created; existing elements not set
    are left unchanged. Of the reserved metadata elements, only "_owner", "_target",
    "_profile", "_status", and "_export" may be set (unless the user is the EZID
    administrator). The "_crossref" element may be set only in certain situations. The
    successful return is a string that includes the canonical, qualified form of the
    identifier, as in:

      success: doi:10.5060/FOO

    Unsuccessful returns include the strings:

      error: forbidden
      error: bad request - subreason...
      error: internal server error
      error: concurrency limit exceeded
    """
    nqidentifier = impl.util.normalizeIdentifier(identifier)
    if nqidentifier is None:
        return "error: bad request - invalid identifier"
    tid = uuid.uuid1()
    if not internalCall:
        if not _acquireIdentifierLock(nqidentifier, user.username):
            return "error: concurrency limit exceeded"
    try:
        impl.log.begin(
            tid,
            "setMetadata",
            nqidentifier,
            user.username,
            user.pid,
            user.group.groupname,
            user.group.pid,
            *[a for p in list(metadata.items()) for a in p],
        )

        si = ezidapp.models.identifier.getIdentifier(nqidentifier)
        if not impl.policy.authorizeUpdate(user, si):
            impl.log.forbidden(tid)
            return "error: forbidden"
        previousOwner = si.owner
        si.updateFromUntrustedLegacy(metadata, allowRestrictedSettings=user.isSuperuser)
        if si.isCrossref and not si.isReserved and updateExternalServices:
            si.crossrefStatus = ezidapp.models.identifier.Identifier.CR_WORKING
            si.crossrefMessage = ""
        if "_updated" not in metadata:
            si.updateTime = ""
        si.my_full_clean()
        if si.owner != previousOwner:
            if not impl.policy.authorizeOwnershipChange(user, previousOwner, si.owner):
                impl.log.badRequest(tid)
                return "error: bad request - ownership change prohibited"

        with django.db.transaction.atomic():
            si.save()
            impl.enqueue.enqueue(si, "update", updateExternalServices)

    except ezidapp.models.identifier.Identifier.DoesNotExist:
        impl.log.badRequest(tid)
        return "error: bad request - no such identifier"
    except django.core.exceptions.ValidationError as e:
        impl.log.badRequest(tid)
        return "error: bad request - " + impl.util.formatValidationError(e)
    except Exception as e:
        impl.log.error(tid, e)
        if hasattr(sys, 'is_running_under_pytest'):
            raise
        return "error: internal server error"
    else:
        impl.log.success(tid)
        return "success: " + nqidentifier
    finally:
        if not internalCall:
            _releaseIdentifierLock(nqidentifier, user.username)


def deleteIdentifier(identifier, user, updateExternalServices=True):
    """Delete an identifier having the given qualified name, e.g.,
    "doi:10.5060/FOO". 'user' is the requestor and should be an authenticated
    User object. The successful return is a string that includes the
    canonical, qualified form of the now-nonexistent identifier, as in:

      success: doi:/10.5060/FOO

    Unsuccessful returns include the strings:

      error: forbidden
      error: bad request - subreason...
      error: internal server error
      error: concurrency limit exceeded
    """
    nqidentifier = impl.util.normalizeIdentifier(identifier)
    if nqidentifier is None:
        return "error: bad request - invalid identifier"
    tid = uuid.uuid1()
    if not _acquireIdentifierLock(nqidentifier, user.username):
        return "error: concurrency limit exceeded"
    try:
        impl.log.begin(
            tid,
            "deleteIdentifier",
            nqidentifier,
            user.username,
            user.pid,
            user.group.groupname,
            user.group.pid,
        )

        si = ezidapp.models.identifier.getIdentifier(nqidentifier)
        if not impl.policy.authorizeDelete(user, si):
            impl.log.forbidden(tid)
            return "error: forbidden"
        if not si.isReserved and not user.isSuperuser:
            impl.log.badRequest(tid)
            return "error: bad request - identifier status does not support deletion"

        with django.db.transaction.atomic():
            impl.enqueue.enqueue(si, "delete", updateExternalServices)
            si.delete()

    except ezidapp.models.identifier.Identifier.DoesNotExist:
        impl.log.badRequest(tid)
        return "error: bad request - no such identifier"
    except Exception as e:
        impl.log.error(tid, e)
        if hasattr(sys, 'is_running_under_pytest'):
            raise
        return "error: internal server error"
    else:
        impl.log.success(tid)
        return "success: " + nqidentifier
    finally:
        _releaseIdentifierLock(nqidentifier, user.username)
