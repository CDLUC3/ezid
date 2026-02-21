#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Shared state

Simple locking mechanism to ensure that, in a multi-threaded environment, no given
identifier is operated on by two threads simultaneously. Additionally, we enforce a
per-user throttle on concurrent operations. _activeUsers maps local usernames to the
number of operations currently being performed by that user. For status reporting
purposes, _waitingUsers similarly maps local usernames to numbers of waiting requests.
If _paused is true, no new locks are granted, but the mechanism otherwise operates
normally.
"""

import threading

import django.conf

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
        or _activeUsers.get(user, 0)
        >= django.conf.settings.MAX_CONCURRENT_OPERATIONS_PER_USER
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
    _lock.notify_all()
    _lock.release()
