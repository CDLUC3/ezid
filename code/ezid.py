# =============================================================================
#
# EZID :: ezid.py
#
# Main functionality.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2010, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.core.exceptions
import django.db.transaction
import django.db.utils
import threading
import uuid

import config
import ezidapp.models
import log
import noid_nog
import policy
import util
import util2

_perUserThreadLimit = None
_perUserThrottle = None

def loadConfig ():
  global _perUserThreadLimit, _perUserThrottle
  _perUserThreadLimit = int(config.get("DEFAULT.max_threads_per_user"))
  _perUserThrottle =\
    int(config.get("DEFAULT.max_concurrent_operations_per_user"))

# Simple locking mechanism to ensure that, in a multi-threaded
# environment, no given identifier is operated on by two threads
# simultaneously.  Additionally, we enforce a per-user throttle on
# concurrent operations.  _activeUsers maps local usernames to the
# number of operations currently being performed by that user.  For
# status reporting purposes, _waitingUsers similarly maps local
# usernames to numbers of waiting requests.  If _paused is true, no
# new locks are granted, but the mechanism otherwise operates
# normally.

_lockedIdentifiers = set()
_activeUsers = {}
_waitingUsers = {}
_lock = threading.Condition()
_paused = False

def _incrementCount (d, k):
  d[k] = d.get(k, 0) + 1

def _decrementCount (d, k):
  if d[k] == 1:
    del d[k]
  else:
    d[k] = d[k] - 1

def _acquireIdentifierLock (identifier, user):
  _lock.acquire()
  while _paused or identifier in _lockedIdentifiers or\
    _activeUsers.get(user, 0) >= _perUserThrottle:
    if _activeUsers.get(user, 0) + _waitingUsers.get(user, 0) >=\
      _perUserThreadLimit:
      _lock.release()
      return False
    _incrementCount(_waitingUsers, user)
    _lock.wait()
    _decrementCount(_waitingUsers, user)
  _incrementCount(_activeUsers, user)
  _lockedIdentifiers.add(identifier)
  _lock.release()
  return True

def _releaseIdentifierLock (identifier, user):
  _lock.acquire()
  _lockedIdentifiers.remove(identifier)
  _decrementCount(_activeUsers, user)
  _lock.notifyAll()
  _lock.release()

def getStatus ():
  """
  Returns a tuple consisting of two dictionaries and a boolean flag.
  The first dictionary maps local usernames to the number of
  operations currently being performed by that user; the sum of the
  dictionary values is the total number of operations currently being
  performed.  The second dictionary similarly maps local usernames to
  numbers of waiting requests.  The boolean flag indicates if the
  server is currently paused.
  """
  _lock.acquire()
  try:
    return (_activeUsers.copy(), _waitingUsers.copy(), _paused)
  finally:
    _lock.release()

def pause (newValue):
  """
  Sets or unsets the paused flag and returns the flag's previous
  value.  If the server is paused, no new identifier locks are granted
  and all requests are forced to wait.
  """
  global _paused
  _lock.acquire()
  try:
    oldValue = _paused
    _paused = newValue
    if not _paused: _lock.notifyAll()
    return oldValue
  finally:
    _lock.release()

def mintIdentifier (shoulder, user, metadata={}):
  """
  Mints an identifier under the given qualified shoulder, e.g.,
  "doi:10.5060/".  'user' is the requestor and should be an
  authenticated StoreUser object.  'metadata' should be a dictionary
  of element (name, value) pairs.  If an initial target URL is not
  supplied, the identifier is given a self-referential target URL.
  The successful return is a string that includes the canonical,
  qualified form of the new identifier, as in:

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
  try:
    log.begin(tid, "mintIdentifier", shoulder, user.username, user.pid,
      user.group.groupname, user.group.pid)
    s = ezidapp.models.getExactShoulderMatch(shoulder)
    if s == None:
      log.badRequest(tid)
      return "error: bad request - no such shoulder"
    if s.isUuid:
      identifier = "uuid:" + str(uuid.uuid1())
    else:
      if s.minter == "":
        log.badRequest(tid)
        return "error: bad request - shoulder does not support minting"
      # Minters always return unqualified ARKs.
      ark = noid_nog.getMinter(s.minter).mintIdentifier()
      if s.isArk:
        identifier = "ark:/" + ark
      elif s.isDoi:
        doi = util.shadow2doi(ark)
        assert util.doi2shadow(doi) == ark, "invalid DOI shadow ARK"
        identifier = "doi:" + doi
      else:
        assert False, "unhandled case"
      assert identifier.startswith(s.prefix),\
        "minted identifier does not match shoulder"
  except Exception, e:
    log.error(tid, e)
    return "error: internal server error"
  else:
    log.success(tid, identifier)
  return createIdentifier(identifier, user, metadata)

def createIdentifier (identifier, user, metadata={}, updateIfExists=False):
  """
  Creates an identifier having the given qualified name, e.g.,
  "doi:10.5060/FOO".  'user' is the requestor and should be an
  authenticated StoreUser object.  'metadata' should be a dictionary
  of element (name, value) pairs.  If an initial target URL is not
  supplied, the identifier is given a self-referential target URL.
  The successful return is a string that includes the canonical,
  qualified form of the new identifier, as in:

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
  nqidentifier = util.normalizeIdentifier(identifier)
  if nqidentifier == None: return "error: bad request - invalid identifier"
  tid = uuid.uuid1()
  if not _acquireIdentifierLock(nqidentifier, user.username):
    return "error: concurrency limit exceeded"
  try:
    log.begin(tid, "createIdentifier", nqidentifier, user.username, user.pid,
      user.group.groupname, user.group.pid,
      *[a for p in metadata.items() for a in p])
    if not policy.authorizeCreate(user, nqidentifier):
      log.forbidden(tid)
      return "error: forbidden"
    si = ezidapp.models.StoreIdentifier(identifier=nqidentifier,
      owner=(None if user == ezidapp.models.AnonymousUser else user))
    si.updateFromUntrustedLegacy(metadata,
      allowRestrictedSettings=user.isSuperuser)
    if si.isDoi:
      s = ezidapp.models.getLongestShoulderMatch(si.identifier)
      # Should never happen.
      assert s != None, "no matching shoulder found"
      if s.isDatacite:
        if si.datacenter == None: si.datacenter = s.datacenter
      elif s.isCrossref:
        if not si.isCrossref:
          if si.isReserved:
            si.crossrefStatus = ezidapp.models.StoreIdentifier.CR_RESERVED
          else:
            si.crossrefStatus = ezidapp.models.StoreIdentifier.CR_WORKING
      else:
        assert False, "unhandled case"
    si.my_full_clean()
    if si.owner != user:
      if not policy.authorizeOwnershipChange(user, user, si.owner):
        log.badRequest(tid)
        return "error: bad request - ownership change prohibited"
    with django.db.transaction.atomic():
      si.save()
      ezidapp.models.update_queue.enqueue(si, "create")
  except django.core.exceptions.ValidationError, e:
    log.badRequest(tid)
    return "error: bad request - " + util.formatValidationError(e)
  except django.db.utils.IntegrityError:
    log.badRequest(tid)
    if updateIfExists:
      return setMetadata(identifier, user, metadata, internalCall=True)
    else:
      return "error: bad request - identifier already exists"
  except Exception, e:
    log.error(tid, e)
    return "error: internal server error"
  else:
    log.success(tid)
    if si.isDoi:
      return "success: %s | %s" % (nqidentifier, si.arkAlias)
    else:
      return "success: " + nqidentifier
  finally:
    _releaseIdentifierLock(nqidentifier, user.username)

def getMetadata (identifier, user=ezidapp.models.AnonymousUser,
  prefixMatch=False):
  """
  Returns all metadata for a given qualified identifier, e.g.,
  "doi:10.5060/FOO".  'user' is the requestor and should be an
  authenticated StoreUser object.  The successful return is a pair
  (status, dictionary) where 'status' is a string that includes the
  canonical, qualified form of the identifier, as in:

    success: doi:10.5060/FOO

  and 'dictionary' contains element (name, value) pairs.  Unsuccessful
  returns include the strings:

    error: forbidden
    error: bad request - subreason...
    error: internal server error
    error: concurrency limit exceeded

  If 'prefixMatch' is true, prefix matching is enabled and the
  returned identifier is the longest identifier that matches a
  (possibly proper) prefix of the requested identifier.  In such a
  case, the status string resembles:

    success: doi:10.5060/FOO in_lieu_of doi:10.5060/FOOBAR
  """
  nqidentifier = util.normalizeIdentifier(identifier)
  if nqidentifier == None: return "error: bad request - invalid identifier"
  tid = uuid.uuid1()
  if not _acquireIdentifierLock(nqidentifier, user.username):
    return "error: concurrency limit exceeded"
  try:
    log.begin(tid, "getMetadata", nqidentifier, user.username, user.pid,
      user.group.groupname, user.group.pid, str(prefixMatch))
    si = ezidapp.models.getIdentifier(nqidentifier, prefixMatch)
    if not policy.authorizeView(user, si):
      log.forbidden(tid)
      return "error: forbidden"
    d = si.toLegacy()
    util2.convertLegacyToExternal(d)
    if si.isDoi: d["_shadowedby"] = si.arkAlias
    log.success(tid)
    if prefixMatch and si.identifier != nqidentifier:
      return ("success: %s in_lieu_of %s" % (si.identifier, nqidentifier), d)
    else:
      return ("success: " + nqidentifier, d)
  except ezidapp.models.StoreIdentifier.DoesNotExist:
    log.badRequest(tid)
    return "error: bad request - no such identifier"
  except Exception, e:
    log.error(tid, e)
    return "error: internal server error"
  finally:
    _releaseIdentifierLock(nqidentifier, user.username)

def setMetadata (identifier, user, metadata, updateExternalServices=True,
  internalCall=False):
  """
  Sets metadata elements of a given qualified identifier, e.g.,
  "doi:10.5060/FOO".  'user' is the requestor and should be an
  authenticated StoreUser object.  'metadata' should be a dictionary
  of element (name, value) pairs.  If an element being set already
  exists, it is overwritten, if not, it is created; existing elements
  not set are left unchanged.  Of the reserved metadata elements, only
  "_owner", "_target", "_profile", "_status", and "_export" may be set
  (unless the user is the EZID administrator).  The "_crossref"
  element may be set only in certain situations.  The successful
  return is a string that includes the canonical, qualified form of
  the identifier, as in:

    success: doi:10.5060/FOO

  Unsuccessful returns include the strings:

    error: forbidden
    error: bad request - subreason...
    error: internal server error
    error: concurrency limit exceeded
  """
  nqidentifier = util.normalizeIdentifier(identifier)
  if nqidentifier == None: return "error: bad request - invalid identifier"
  tid = uuid.uuid1()
  if not internalCall:
    if not _acquireIdentifierLock(nqidentifier, user.username):
      return "error: concurrency limit exceeded"
  try:
    log.begin(tid, "setMetadata", nqidentifier, user.username, user.pid,
      user.group.groupname, user.group.pid,
      *[a for p in metadata.items() for a in p])
    si = ezidapp.models.getIdentifier(nqidentifier)
    if not policy.authorizeUpdate(user, si):
      log.forbidden(tid)
      return "error: forbidden"
    previousOwner = si.owner
    si.updateFromUntrustedLegacy(metadata,
      allowRestrictedSettings=user.isSuperuser)
    if si.isCrossref and not si.isReserved and updateExternalServices:
      si.crossrefStatus = ezidapp.models.StoreIdentifier.CR_WORKING
      si.crossrefMessage = ""
    if "_updated" not in metadata: si.updateTime = ""
    si.my_full_clean()
    if si.owner != previousOwner:
      if not policy.authorizeOwnershipChange(user, previousOwner, si.owner):
        log.badRequest(tid)
        return "error: bad request - ownership change prohibited"
    with django.db.transaction.atomic():
      si.save()
      ezidapp.models.update_queue.enqueue(si, "update", updateExternalServices)
  except ezidapp.models.StoreIdentifier.DoesNotExist:
    log.badRequest(tid)
    return "error: bad request - no such identifier"
  except django.core.exceptions.ValidationError, e:
    log.badRequest(tid)
    return "error: bad request - " + util.formatValidationError(e)
  except Exception, e:
    log.error(tid, e)
    return "error: internal server error"
  else:
    log.success(tid)
    return "success: " + nqidentifier
  finally:
    if not internalCall: _releaseIdentifierLock(nqidentifier, user.username)

def deleteIdentifier (identifier, user, updateExternalServices=True):
  """
  Deletes an identifier having the given qualified name, e.g.,
  "doi:10.5060/FOO".  'user' is the requestor and should be an
  authenticated StoreUser object.  The successful return is a string
  that includes the canonical, qualified form of the now-nonexistent
  identifier, as in:

    success: doi:/10.5060/FOO

  Unsuccessful returns include the strings:

    error: forbidden
    error: bad request - subreason...
    error: internal server error
    error: concurrency limit exceeded
  """
  nqidentifier = util.normalizeIdentifier(identifier)
  if nqidentifier == None: return "error: bad request - invalid identifier"
  tid = uuid.uuid1()
  if not _acquireIdentifierLock(nqidentifier, user.username):
    return "error: concurrency limit exceeded"
  try:
    log.begin(tid, "deleteIdentifier", nqidentifier, user.username, user.pid,
      user.group.groupname, user.group.pid)
    si = ezidapp.models.getIdentifier(nqidentifier)
    if not policy.authorizeDelete(user, si):
      log.forbidden(tid)
      return "error: forbidden"
    if not si.isReserved and not user.isSuperuser:
      log.badRequest(tid)
      return "error: bad request - identifier status does not support deletion"
    with django.db.transaction.atomic():
      si.delete()
      ezidapp.models.update_queue.enqueue(si, "delete", updateExternalServices)
  except ezidapp.models.StoreIdentifier.DoesNotExist:
    log.badRequest(tid)
    return "error: bad request - no such identifier"
  except Exception, e:
    log.error(tid, e)
    return "error: internal server error"
  else:
    log.success(tid)
    return "success: " + nqidentifier
  finally:
    _releaseIdentifierLock(nqidentifier, user.username)
