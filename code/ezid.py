# =============================================================================
#
# EZID :: ezid.py
#
# Main functionality.
#
# All identifier metadata is stored in a single "bind" noid instance.
# Metadata for an ARK identifier (e.g., ark:/13030/foo) is keyed by
# the canonical form of that identifier (see util.validateArk);
# metadata for a non-ARK identifier (e.g., doi:10.5060/FOO) is keyed
# by the identifier's shadow ARK (e.g., ark:/b5060/foo).  The
# supported non-ARK identifiers include DOIs and URNs.
#
# The shadow ARK for a non-ARK identifier is computable by a simple
# mapping (see util.doi2shadow, util.urnUuid2shadow, etc.); the
# reverse mapping is not simple and requires a lookup.
#
# Shadow ARKs provide a technical means of storing metadata for
# non-ARK identifiers, but they're also identifiers in their own
# right: they're advertised to users and they independently resolve.
# But while a non-ARK identifier and its shadow ARK may have different
# target URLs, they otherwise share all metadata (owner, creation
# time, etc.), and so they should be considered closely-related
# identifiers.
#
# ***TRANSITION ALERT*** Shadow ARKs are being phased out.  _t and
# _st, _t1 and _st1, and _u and _su are clamped now to have the same
# value (though differing legacy values are still in place).
# Transitional code is marked with "TRANSITION" below.  When it has
# been confirmed that clients won't miss the old functionality, shadow
# ARKs will be eliminated entirely.
#
# Identifier metadata is structured as element (name, value) pairs.
# Element names are not repeatable.  Names are arbitrary and
# uncontrolled, but those beginning with an underscore are reserved
# for internal use by EZID and other services.  Reserved element names
# have two forms: a short form used for storage and a longer, more
# readable form used in communicating with clients.  In the following
# table, it may appear that different elements have the same long form
# name, but the context always makes it clear which is being returned.
#
# stored | transmitted |
# label  | label       | meaning
# -------+-------------+----------------------------------------------
# _o     | _owner      | The identifier's owner.  The owner is stored
#        |             | as a persistent identifier (e.g.,
#        |             | "ark:/13030/foo") but returned as a local
#        |             | name (e.g., "ryan").  The owner may also be
#        |             | "anonymous".  For a shadow ARK, applies to
#        |             | both the shadow ARK and shadowed identifier.
# _g     | _ownergroup | The identifier's owning group, which is often
#        |             | but not necessarily the identifier's owner's
#        |             | current group.  The group is stored as a
#        |             | persistent identifier (e.g.,
#        |             | "ark:/13030/bar") but returned as a local
#        |             | name (e.g., "dryad").  The group may also be
#        |             | "anonymous".  For a shadow ARK, applies to
#        |             | both the shadow ARK and shadowed identifier.
# _c     | _created    | The time the identifier was created expressed
#        |             | as a Unix timestamp, e.g., "1280889190".  For
#        |             | a shadow ARK, applies to both the shadow ARK
#        |             | and shadowed identifier.
# _u     | _updated    | The time the identifier was last modified
#        |             | expressed as a Unix timestamp, e.g.,
#        |             | "1280889190".  For a shadow ARK, applies to
#        |             | the ARK only, not the shadowed identifier.
# _t     | _target     | The identifier's target URL, e.g.,
#        |             | "http://foo.com/bar".  For a shadow ARK,
#        |             | applies to the ARK only, not the shadowed
#        |             | identifier.  (See _t1 below for
#        |             | qualifications.)
# _s     | _shadows    | Shadow ARKs only.  The shadowed identifier,
#        |             | e.g., "doi:10.5060/FOO".
# _su    | _updated    | Shadow ARKs only.  The time the shadowed
#        |             | identifier was last modified expressed as a
#        |             | Unix timestamp, e.g., "1280889190".
# _st    | _target     | Shadow ARKs only.  The shadowed identifier's
#        |             | target URL, e.g., "http://foo.com/bar".  (See
#        |             | _st1 below for qualifications.)
#        | _shadowedby | Shadowed identifiers only.  The identifier's
#        |             | shadow ARK, e.g., "ark:/b5060/foo".  This is
#        |             | computed, not stored.
# _p     | _profile    | The identifier's preferred metadata profile,
#        |             | e.g., "erc".  See module 'metadata' for more
#        |             | information on profiles.  A profile does not
#        |             | place any requirements on what metadata
#        |             | elements must be present or restrict what
#        |             | metadata elements can be present.  By
#        |             | convention, the element names of a profile
#        |             | are prefixed with the profile name, e.g.,
#        |             | "erc.who".  For a shadow ARK, applies to both
#        |             | the shadow ARK and shadowed identifier.
# _is    | _status     | Identifier status.  If present, either
#        |             | "reserved" or "unavailable"; if not present,
#        |             | effectively has the value "public".  If
#        |             | "unavailable", a reason may follow separated
#        |             | by a pipe character, e.g., "unavailable |
#        |             | withdrawn by author".  Always returned.  For
#        |             | a shadow ARK, applies to both the shadow ARK
#        |             | and shadowed identifier.
# _t1    |             | If the identifier status is "public", not
#        |             | present; otherwise, if the identifier status
#        |             | is "reserved" or "unavailable", the target
#        |             | URL as set by the client.  (In these latter
#        |             | cases _t is set to an EZID-defined URL.)  Not
#        |             | returned.
# _st1   |             | Shadow ARKs only.  If the identifier status
#        |             | is "public", not present; otherwise, if the
#        |             | identifier status is "reserved" or
#        |             | "unavailable", the shadowed identifier's
#        |             | target URL as set by the client.  (In these
#        |             | latter cases _st is set to an EZID-defined
#        |             | URL.)  Not returned.
# _x     | _export     | Export control.  If present, has the value
#        |             | "no"; if not present, effectively has the
#        |             | value "yes".  Determines if the identifier is
#        |             | publicized by exporting it to external
#        |             | indexing and harvesting services.  Always
#        |             | returned.  For a shadow ARK, applies to both
#        |             | the shadow ARK and shadowed identifier.
# _d     | _datacenter | DOIs only.  The DataCite datacenter at which
#        |             | the identifier is registered, e.g.,
#        |             | "CDL.DRYAD" (or will be registered, in the
#        |             | case of a reserved identifier).
# _cr    | _crossref   | DOIs only.  If present, indicates that the
#        |             | identifier is registered with Crossref (or,
#        |             | in the case of a reserved identifier, will be
#        |             | registered), and also indicates the status of
#        |             | the registration process.  Syntactically, has
#        |             | the value "yes" followed by a pipe character
#        |             | followed by a status message, e.g., "yes |
#        |             | successfully registered".
#
# Element names and values are first UTF-8 encoded, and then
# non-graphic ASCII characters and a few other reserved characters are
# percent-encoded; see util.encode{3,4} and util.decode.
#
# ARK identifiers that identify users and groups ("agent identifiers")
# are treated specially by EZID.  Such identifiers are identified by
# the presence of an _ezid_role metadata element, which may have the
# value "user" or "group".  Additional metadata elements cache
# contact and other administrative information.  Agent identifiers are
# owned by the EZID administrator, and to protect user privacy, they
# may be viewed by the EZID administrator only.
#
# As a kind of Easter egg, the _external_updates metadata element,
# which takes the value "yes" or "no", may be specified on
# setMetadata calls (only) to control the updateExternalServices
# argument.  The element is not stored.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2010, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.core.validators
import re
import threading
import time
import urllib
import uuid

import config
import crossref
import datacite
import ezidapp.models
import ezidapp.models.validation
import log
import noid_egg
import noid_nog
import policy
import store
import util

_ezidUrl = None
_noidReadEnabled = None
_defaultDoiProfile = None
_defaultArkProfile = None
_defaultUrnUuidProfile = None
_perUserThreadLimit = None
_perUserThrottle = None

def _loadConfig ():
  global _ezidUrl, _noidReadEnabled, _defaultDoiProfile, _defaultArkProfile
  global _defaultUrnUuidProfile
  global _perUserThreadLimit, _perUserThrottle
  _ezidUrl = config.get("DEFAULT.ezid_base_url")
  _noidReadEnabled = (config.get("binder.read_enabled").lower() == "true")
  _defaultDoiProfile = config.get("DEFAULT.default_doi_profile")
  _defaultArkProfile = config.get("DEFAULT.default_ark_profile")
  _defaultUrnUuidProfile = config.get("DEFAULT.default_urn_uuid_profile")
  _perUserThreadLimit = int(config.get("DEFAULT.max_threads_per_user"))
  _perUserThrottle =\
    int(config.get("DEFAULT.max_concurrent_operations_per_user"))

_loadConfig()
config.registerReloadListener(_loadConfig)

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

_labelMapping = {
  "_o": "_owner",
  "_g": "_ownergroup",
  "_c": "_created",
  "_u": "_updated",
  "_t": "_target",
  "_s": "_shadows",
  "_su": "_updated",
  "_st": "_target",
  "_p": "_profile",
  "_is": "_status",
  "_x": "_export",
  "_d": "_datacenter",
  "_cr": "_crossref"
}

def _oneline (s):
  return re.sub("\s", " ", s)

def _defaultTarget (identifier):
  return "%s/id/%s" % (_ezidUrl, urllib.quote(identifier, ":/"))

def _tombstoneTarget (identifier):
  return "%s/tombstone/id/%s" % (_ezidUrl, urllib.quote(identifier, ":/"))

def _softUpdate (td, sd):
  for k, v in sd.items():
    if k not in td: td[k] = v

_userSettableReservedElements = ["_owner", "_export", "_profile", "_status",
  "_target", "_crossref"]

_crossrefDoiRE = re.compile("doi:10\.[1-9]\d{3,4}/[-\w.;()/]+$")

def _validateMetadata (identifier, user, metadata):
  """
  Validates and normalizes 'metadata', a dictionary of (name, value)
  pairs; 'metadata' is modified in place.  In the process, any
  reserved element names are converted to their internal forms.
  Returns None on success or a string error message.  'identifier' is
  the identifier in question, and should be qualified and normalized,
  e.g., "doi:10.5060/FOO".  'user' is the requestor and should be an
  authenticated StoreUser object.
  """
  if any(map(lambda k: len(k) == 0, metadata)): return "empty element name"
  if "_coowners" in metadata: return "element '_coowners' is deprecated"
  if not user.isSuperuser and any(map(lambda k: k.startswith("_") and\
    k not in _userSettableReservedElements, metadata)):
    return "use of reserved element name"
  if "_owner" in metadata:
    o = ezidapp.models.getUserByUsername(metadata["_owner"])
    if o == None or o == ezidapp.models.AnonymousUser:
      return "element '_owner': no such user"
    metadata["_o"] = o.pid
    metadata["_g"] = o.group.pid
    del metadata["_owner"]
  if "_export" in metadata:
    metadata["_x"] = metadata["_export"].strip().lower()
    if metadata["_x"] not in ["yes", "no"]: return "invalid export flag value"
    del metadata["_export"]
  if "_profile" in metadata:
    if metadata["_profile"].strip() != "":
      p = metadata["_profile"].strip()
      # The following matches the validation done by the forthcoming
      # Identifier model.
      if len(p) > 32 or not re.match("^[a-z0-9]+([-_.][a-z0-9]+)*$", p):
        return "invalid profile name"
      metadata["_p"] = p
    else:
      if identifier.startswith("doi:"):
        metadata["_p"] = _defaultDoiProfile
      elif identifier.startswith("ark:/"):
        metadata["_p"] = _defaultArkProfile
      elif identifier.startswith("urn:uuid:"):
        metadata["_p"] = _defaultUrnUuidProfile
      else:
        assert False, "unhandled case"
    del metadata["_profile"]
  if "_status" in metadata:
    metadata["_is"] = metadata["_status"].strip()
    m = re.match("unavailable($| *\|(.*))", metadata["_is"])
    if m:
      reason = (m.group(2) or "").strip()
      if len(reason) > 0:
        metadata["_is"] = "unavailable | " + reason
      else:
        metadata["_is"] = "unavailable"
    elif metadata["_is"] not in ["public", "reserved"]:
      return "invalid identifier status"
    del metadata["_status"]
  if "_target" in metadata:
    e = "_t" if identifier.startswith("ark:/") else "_st"
    t = metadata["_target"].strip()
    if t != "":
      # The following matches the validation and normalization done by
      # the forthcoming Identifier model.
      try:
        assert len(t) <= 2000
        django.core.validators.URLValidator()(t)
      except:
        return "invalid target URL"
      scheme, rest = t.split(":", 1)
      metadata[e] = "%s:%s" % (scheme.lower(), rest)
    else:
      metadata[e] = _defaultTarget(identifier)
    del metadata["_target"]
  if "crossref" in metadata and metadata["crossref"].strip() != "":
    try:
      metadata["crossref"] = crossref.validateBody(metadata["crossref"])
    except AssertionError, e:
      return "element 'crossref': " + _oneline(str(e))
  if "_crossref" in metadata:
    # On input, we allow values "yes" and "no".  Subsequent checks
    # will place limits on when those values can be specified.  Note
    # that the stored value for _cr is different and computed.  Subtle
    # point: when EZID internally sets _cr to computed values, it does
    # so by referencing the element as "_cr" (which it can do since it
    # acts as the EZID administrator), thereby bypassing this
    # validation entirely.
    if not identifier.startswith("doi:"):
      return "only DOI identifiers can be registered with Crossref"
    # Crossref imposes additional restrictions on DOI syntax.
    if not _crossrefDoiRE.match(identifier):
      return "identifier does not meet Crossref syntax requirements"
    metadata["_cr"] = metadata["_crossref"].strip().lower()
    if metadata["_cr"] not in ["yes", "no"]:
      return "element '_crossref': invalid input value"
    del metadata["_crossref"]
  return None

def _validateDatacite (identifier, metadata, completeCheck):
  """
  Similar to _validateMetadata, but performs DataCite-related
  validations.  If 'completeCheck' is true, the DataCite XML record
  (if any) is fully schema validated, and we check that DataCite
  metadata requirements are satisfied (XML record or not).  (These
  checks have been split out from _validateMetadata because of the
  'completeCheck' flag, which varies depending on the identifier
  state.)
  """
  if "datacite.resourcetype" in metadata and\
    metadata["datacite.resourcetype"].strip() != "":
    try:
      metadata["datacite.resourcetype"] =\
        ezidapp.models.validation.resourceType(
        metadata["datacite.resourcetype"])
    except:
      return "element 'datacite.resourcetype': invalid resource type"
  # The following checks may fail if we operate on a shadow ARK, ergo...
  if identifier.startswith("ark:/") and "_s" in metadata:
    identifier = metadata["_s"]
  if "datacite" in metadata and metadata["datacite"].strip() != "":
    try:
      metadata["datacite"] = datacite.validateDcmsRecord(identifier,
        metadata["datacite"], schemaValidate=completeCheck)
    except AssertionError, e:
      return "element 'datacite': " + _oneline(str(e))
  if completeCheck and identifier.startswith("doi:"):
    try:
      datacite.formRecord(identifier, metadata)
    except AssertionError, e:
      return "DOI metadata requirements not satisfied: " + str(e)
  return None

def _identifierExists (identifier):
  if _noidReadEnabled:
    return noid_egg.identifierExists(identifier)
  else:
    return store.exists(identifier)

def _getElements (identifier):
  if _noidReadEnabled:
    return noid_egg.getElements(identifier)
  else:
    r = store.get(identifier)
    if r != None:
      return r[0]
    else:
      return None

def mintDoi (prefix, user, metadata={}):
  """
  Mints a DOI identifier under the given scheme-less shoulder, e.g.,
  "10.5060/".  'user' is the requestor and should be an authenticated
  StoreUser object.  'metadata' should be a dictionary of element
  (name, value) pairs.  If an initial target URL is not supplied, the
  identifier is given a self-referential target URL.  The successful
  return is a string that includes the canonical, scheme-less form of
  the new identifier, followed by the new identifier's qualified
  shadow ARK, as in:

    success: 10.5060/FK35717N0H | ark:/b5060/fk35717n0h

  Unsuccessful returns include the strings:

    error: forbidden
    error: bad request - subreason...
    error: internal server error
  """
  qprefix = "doi:" + prefix
  s = ezidapp.models.getExactShoulderMatch(qprefix)
  if s is None: return "error: bad request - unrecognized DOI shoulder"
  tid = uuid.uuid1()
  try:
    log.begin(tid, "mintDoi", prefix, user.username, user.pid,
      user.group.groupname, user.group.pid)
    if not policy.authorizeCreate(user, qprefix):
      log.forbidden(tid)
      return "error: forbidden"
    if s.minter == "":
      log.badRequest(tid)
      return "error: bad request - no minter for shoulder"
    shadowArk = noid_nog.Minter(s.minter).mintIdentifier()
    doi = util.shadow2doi(shadowArk)
    assert doi.startswith(prefix),\
      "minted DOI does not match requested shoulder"
    assert util.doi2shadow(doi) == shadowArk,\
      "minted DOI does not map back to minted shadow ARK"
  except Exception, e:
    log.error(tid, e)
    return "error: internal server error"
  else:
    log.success(tid, doi)
  return createDoi(doi, user, metadata)

def createDoi (doi, user, metadata={}):
  """
  Creates a DOI identifier having the given scheme-less name, e.g.,
  "10.5060/FOO".  The identifier must not already exist.  'user' is
  the requestor and should be an authenticated StoreUser object.
  'metadata' should be a dictionary of element (name, value) pairs.
  If an initial target URL is not supplied, the identifier is given a
  self-referential target URL.  The successful return is a string that
  includes the canonical, scheme-less form of the new identifier,
  followed by the new identifier's qualified shadow ARK, as in:

    success: 10.5060/FOO | ark:/b5060/foo

  Unsuccessful returns include the strings:

    error: forbidden
    error: bad request - subreason...
    error: internal server error
    error: concurrency limit exceeded
  """
  doi = util.validateDoi(doi)
  if not doi: return "error: bad request - invalid DOI identifier"
  qdoi = "doi:" + doi
  shadowArk = util.doi2shadow(doi)
  m = { "_profile": "", "_target": "" }
  m.update(metadata)
  r = _validateMetadata(qdoi, user, m)
  if type(r) is str: return "error: bad request - " + r
  if "_is" in m:
    if m["_is"] == "public":
      del m["_is"]
    elif m["_is"] != "reserved":
      return "error: bad request - invalid identifier status at creation time"
  if m.get("_x", "") == "yes": del m["_x"]
  if m.get("_cr", "") == "no": del m["_cr"]
  if "_cr" in m:
    if "_x" in m:
      return "error: bad request - identifier registered with Crossref " +\
        "must be exported"
    if "_is" not in m and m.get("crossref", "").strip() == "":
      return "error: bad request - Crossref registration requires " +\
        "'crossref' deposit metadata"
  r = _validateDatacite(qdoi, m, "_is" not in m)
  if type(r) is str: return "error: bad request - " + r
  tid = uuid.uuid1()
  if not _acquireIdentifierLock(shadowArk, user.username):
    return "error: concurrency limit exceeded"
  try:
    log.begin(tid, "createDoi", doi, user.username, user.pid,
      user.group.groupname, user.group.pid,
      *[a for p in metadata.items() for a in p])
    if not policy.authorizeCreate(user, qdoi):
      if ezidapp.models.getLongestShoulderMatch(qdoi) != None:
        log.forbidden(tid)
        return "error: forbidden"
      else:
        log.badRequest(tid)
        return "error: bad request - no matching shoulder found"
    if "_o" in m:
      if not policy.authorizeOwnershipChange(user, qdoi, user.pid, m["_o"]):
        log.badRequest(tid)
        return "error: bad request - ownership change prohibited"
    if "_cr" in m:
      if not policy.authorizeCrossref(user, qdoi):
        # Technically it's an authorization error, but it makes more
        # sense to clients to receive a bad request.
        log.badRequest(tid)
        return "error: bad request - Crossref registration is not enabled " +\
          "for user and shoulder"
      if "_is" in m: # reserved
        m["_cr"] = "yes | awaiting status change to public"
      else:
        m["_cr"] = "yes | registration in progress"
    if _identifierExists(shadowArk):
      log.badRequest(tid)
      return "error: bad request - identifier already exists"
    t = str(int(time.time()))
    s = ezidapp.models.getLongestShoulderMatch(qdoi)
    # Should never happen.
    assert s is not None, "shoulder not found"
    _softUpdate(m, { "_o": user.pid, "_g": user.group.pid, "_c": t, "_u": t,
      "_su": t, "_t": _defaultTarget("ark:/" + shadowArk), "_s": qdoi,
      "_d": s.datacenter.symbol })
    if m.get("_is", "public") == "reserved":
      m["_t1"] = m["_t"]
      m["_st1"] = m["_st"]
      m["_st"] = _defaultTarget(qdoi)
    if m.get("_is", "public") == "public" and\
      m.get("crossref", "").strip() != "":
      # Before storing Crossref metadata, fill in the (:tba) sections
      # that were introduced in the validation/normalization process,
      # but only if the identifier is public.  Unfortunately, doing
      # this with the current code architecture requires that the
      # metadata be re-parsed and re-serialized.
      m["crossref"] = crossref.replaceTbas(m["crossref"], doi, m["_st"])
    # TRANSITION BEGIN
    m["_t"] = m["_st"]
    if "_t1" in m: m["_t1"] = m["_st1"]
    # TRANSITION END
    noid_egg.setElements(shadowArk, m)
    log.progress(tid, "noid_egg.setElements")
    store.insert(shadowArk, m)
  except Exception, e:
    log.error(tid, e)
    return "error: internal server error"
  else:
    log.success(tid)
    return "success: " + doi + " | ark:/" + shadowArk
  finally:
    _releaseIdentifierLock(shadowArk, user.username)

def mintArk (prefix, user, metadata={}):
  """
  Mints an ARK identifier under the given scheme-less shoulder, e.g.,
  "13030/fk4".  'user' is the requestor and should be an authenticated
  StoreUser object.  'metadata' should be a dictionary of element
  (name, value) pairs.  If an initial target URL is not supplied, the
  identifier is given a self-referential target URL.  The successful
  return is a string that includes the canonical, scheme-less form of
  the new identifier, as in:

    success: 13030/fk45717n0h

  Unsuccessful returns include the strings:

    error: forbidden
    error: bad request - subreason...
    error: internal server error
  """
  qprefix = "ark:/" + prefix
  s = ezidapp.models.getExactShoulderMatch(qprefix)
  if s is None: return "error: bad request - unrecognized ARK shoulder"
  tid = uuid.uuid1()
  try:
    log.begin(tid, "mintArk", prefix, user.username, user.pid,
      user.group.groupname, user.group.pid)
    if not policy.authorizeCreate(user, qprefix):
      log.forbidden(tid)
      return "error: forbidden"
    if s.minter == "":
      log.badRequest(tid)
      return "error: bad request - no minter for shoulder"
    ark = noid_nog.Minter(s.minter).mintIdentifier()
    assert ark.startswith(prefix),\
      "minted ARK does not match requested shoulder"
  except Exception, e:
    log.error(tid, e)
    return "error: internal server error"
  else:
    log.success(tid, ark)
  return createArk(ark, user, metadata)

def createArk (ark, user, metadata={}):
  """
  Creates an ARK identifier having the given scheme-less name, e.g.,
  "13030/bar".  The identifier must not already exist.  'user' is the
  requestor and should be an authenticated StoreUser object.
  'metadata' should be a dictionary of element (name, value) pairs.
  If an initial target URL is not supplied, the identifier is given a
  self-referential target URL.  The successful return is a string that
  includes the canonical, scheme-less form of the new identifier, as
  in:

    success: 13030/bar

  Unsuccessful returns include the strings:

    error: forbidden
    error: bad request - subreason...
    error: internal server error
    error: concurrency limit exceeded
  """
  ark = util.validateArk(ark)
  if not ark: return "error: bad request - invalid ARK identifier"
  qark = "ark:/" + ark
  m = { "_profile": "", "_target": "" }
  m.update(metadata)
  r = _validateMetadata(qark, user, m)
  if type(r) is str: return "error: bad request - " + r
  if "_is" in m:
    if m["_is"] == "public":
      del m["_is"]
    elif m["_is"] != "reserved":
      return "error: bad request - invalid identifier status at creation time"
  if m.get("_x", "") == "yes": del m["_x"]
  r = _validateDatacite(qark, m, "_is" not in m)
  if type(r) is str: return "error: bad request - " + r
  tid = uuid.uuid1()
  if not _acquireIdentifierLock(ark, user.username):
    return "error: concurrency limit exceeded"
  try:
    log.begin(tid, "createArk", ark, user.username, user.pid,
      user.group.groupname, user.group.pid,
      *[a for p in metadata.items() for a in p])
    if not policy.authorizeCreate(user, qark):
      if ezidapp.models.getLongestShoulderMatch(qark) != None:
        log.forbidden(tid)
        return "error: forbidden"
      else:
        log.badRequest(tid)
        return "error: bad request - no matching shoulder found"
    if "_o" in m:
      if not policy.authorizeOwnershipChange(user, qark, user.pid, m["_o"]):
        log.badRequest(tid)
        return "error: bad request - ownership change prohibited"
    if _identifierExists(ark):
      log.badRequest(tid)
      return "error: bad request - identifier already exists"
    t = str(int(time.time()))
    _softUpdate(m, { "_o": user.pid, "_g": user.group.pid, "_c": t, "_u": t })
    if m.get("_is", "public") == "reserved":
      m["_t1"] = m["_t"]
      m["_t"] = _defaultTarget(qark)
    noid_egg.setElements(ark, m)
    log.progress(tid, "noid_egg.setElements")
    store.insert(ark, m)
  except Exception, e:
    log.error(tid, e)
    return "error: internal server error"
  else:
    log.success(tid)
    return "success: " + ark
  finally:
    _releaseIdentifierLock(ark, user.username)

def mintUrnUuid (user, metadata={}):
  """
  Mints a UUID URN.  'user' is the requestor and should be an
  authenticated StoreUser object.  'metadata' should be a dictionary
  of element (name, value) pairs.  If an initial target URL is not
  supplied, the identifier is given a self-referential target URL.
  The successful return is a string that includes the canonical,
  scheme-less form of the new identifier, followed by the new
  identifier's qualified shadow ARK, as in:

    success: f81d4fae-7dec-11d0-a765-00a0c91e6bf6 | ark:/97720/f81...

  Unsuccessful returns include the strings:

    error: forbidden
    error: bad request - subreason...
    error: internal server error
  """
  return createUrnUuid(uuid.uuid1().urn[9:], user, metadata)

def createUrnUuid (urn, user, metadata={}):
  """
  Creates a UUID URN identifier having the given scheme-less name,
  e.g., "f81d4fae-7dec-11d0-a765-00a0c91e6bf6".  The identifier must
  not already exist.  'user' is the requestor and should be an
  authenticated StoreUser object.  'metadata' should be a dictionary
  of element (name, value) pairs.  If an initial target URL is not
  supplied, the identifier is given a self-referential target URL.
  The successful return is a string that includes the canonical,
  scheme-less form of the new identifier, followed by the new
  identifier's qualified shadow ARK, as in:

    success: f81d4fae-7dec-11d0-a765-00a0c91e6bf6 | ark:/97720/f81...

  Unsuccessful returns include the strings:

    error: forbidden
    error: bad request - subreason...
    error: internal server error
    error: concurrency limit exceeded
  """
  urn = util.validateUrnUuid(urn)
  if not urn: return "error: bad request - invalid UUID URN identifier"
  qurn = "urn:uuid:" + urn
  shadowArk = util.urnUuid2shadow(urn)
  m = { "_profile": "", "_target": "" }
  m.update(metadata)
  r = _validateMetadata(qurn, user, m)
  if type(r) is str: return "error: bad request - " + r
  if "_is" in m:
    if m["_is"] == "public":
      del m["_is"]
    elif m["_is"] != "reserved":
      return "error: bad request - invalid identifier status at creation time"
  if m.get("_x", "") == "yes": del m["_x"]
  r = _validateDatacite(qurn, m, "_is" not in m)
  if type(r) is str: return "error: bad request - " + r
  tid = uuid.uuid1()
  if not _acquireIdentifierLock(shadowArk, user.username):
    return "error: concurrency limit exceeded"
  try:
    log.begin(tid, "createUrnUuid", urn, user.username, user.pid,
      user.group.groupname, user.group.pid,
      *[a for p in metadata.items() for a in p])
    if not policy.authorizeCreate(user, qurn):
      log.forbidden(tid)
      return "error: forbidden"
    if "_o" in m:
      if not policy.authorizeOwnershipChange(user, qurn, user.pid, m["_o"]):
        log.badRequest(tid)
        return "error: bad request - ownership change prohibited"
    if _identifierExists(shadowArk):
      log.badRequest(tid)
      return "error: bad request - identifier already exists"
    t = str(int(time.time()))
    _softUpdate(m, { "_o": user.pid, "_g": user.group.pid, "_c": t, "_u": t,
      "_su": t, "_t": _defaultTarget("ark:/" + shadowArk), "_s": qurn })
    if m.get("_is", "public") == "reserved":
      m["_t1"] = m["_t"]
      m["_st1"] = m["_st"]
      m["_st"] = _defaultTarget(qurn)
    # TRANSITION BEGIN
    m["_t"] = m["_st"]
    if "_t1" in m: m["_t1"] = m["_st1"]
    # TRANSITION END
    noid_egg.setElements(shadowArk, m)
    log.progress(tid, "noid_egg.setElements")
    store.insert(shadowArk, m)
  except Exception, e:
    log.error(tid, e)
    return "error: internal server error"
  else:
    log.success(tid)
    return "success: " + urn + " | ark:/" + shadowArk
  finally:
    _releaseIdentifierLock(shadowArk, user.username)

def mintIdentifier (prefix, user, metadata={}):
  """
  Mints an identifier under the given qualified shoulder, e.g.,
  "doi:10.5060/".  'user' is the requestor and should be an
  authenticated StoreUser object.  'metadata' should be a dictionary
  of element (name, value) pairs.  If an initial target URL is not
  supplied, the identifier is given a self-referential target URL.
  The successful return is a string that includes the canonical,
  qualified form of the new identifier, as in:

    success: ark:/95060/fk35717n0h

  For non-ARK identifiers, the string also includes the qualified
  shadow ARK, as in:

    success: doi:10.5060/FK35717N0H | ark:/b5060/fk35717n0h

  Unsuccessful returns include the strings:

    error: forbidden
    error: bad request - subreason...
    error: internal server error
  """
  if prefix.startswith("doi:"):
    s = mintDoi(prefix[4:], user, metadata)
    if s.startswith("success: "):
      return "success: doi:" + s[9:]
    else:
      return s
  elif prefix.startswith("ark:/"):
    s = mintArk(prefix[5:], user, metadata)
    if s.startswith("success: "):
      return "success: ark:/" + s[9:]
    else:
      return s
  elif prefix == "urn:uuid:":
    s = mintUrnUuid(user, metadata)
    if s.startswith("success: "):
      return "success: urn:uuid:" + s[9:]
    else:
      return s
  else:
    return "error: bad request - unrecognized identifier scheme"

def createIdentifier (identifier, user, metadata={}):
  """
  Creates an identifier having the given qualified name, e.g.,
  "doi:10.5060/FOO".  'user' is the requestor and should be an
  authenticated StoreUser object.  'metadata' should be a dictionary
  of element (name, value) pairs.  If an initial target URL is not
  supplied, the identifier is given a self-referential target URL.
  The successful return is a string that includes the canonical,
  qualified form of the new identifier, as in:

    success: ark:/95060/foo

  For non-ARK identifiers, the string also includes the qualified
  shadow ARK, as in:

    success: doi:10.5060/FOO | ark:/b5060/foo

  Unsuccessful returns include the strings:

    error: forbidden
    error: bad request - subreason...
    error: internal server error
  """
  if identifier.startswith("doi:"):
    s = createDoi(identifier[4:], user, metadata)
    if s.startswith("success: "):
      return "success: doi:" + s[9:]
    else:
      return s
  elif identifier.startswith("ark:/"):
    s = createArk(identifier[5:], user, metadata)
    if s.startswith("success: "):
      return "success: ark:/" + s[9:]
    else:
      return s
  elif identifier.startswith("urn:uuid:"):
    s = createUrnUuid(identifier[9:], user, metadata)
    if s.startswith("success: "):
      return "success: urn:uuid:" + s[9:]
    else:
      return s
  else:
    return "error: bad request - unrecognized identifier scheme"

def convertMetadataDictionary (d, ark, shadowArkView=False):
  """
  Converts a metadata dictionary from internal form (i.e., as stored)
  to external form (i.e., as returned to clients).  The dictionary is
  modified in place.  'ark' is the unqualified ARK identifier (e.g.,
  "13030/foo") to which the metadata belongs.  If the dictionary is
  for a non-ARK identifier and 'shadowArkView' is true, the dictionary
  is converted to reflect the shadow ARK; otherwise, it reflects the
  shadowed identifier.
  """
  if d.get("_is", "public") != "public":
    d["_t"] = d["_t1"]
    del d["_t1"]
    if "_st1" in d:
      d["_st"] = d["_st1"]
      del d["_st1"]
  if "_s" in d:
    if shadowArkView:
      del d["_su"]
      del d["_st"]
    else:
      del d["_u"]
      del d["_t"]
      del d["_s"]
      d["_shadowedby"] = "ark:/" + ark
  for k in filter(lambda k: k.startswith("_"), d):
    if k in _labelMapping:
      d[_labelMapping[k]] = d[k]
      del d[k]
  d["_owner"] = ezidapp.models.getUserByPid(d["_owner"]).username
  d["_ownergroup"] = ezidapp.models.getGroupByPid(d["_ownergroup"]).groupname
  if "_status" not in d: d["_status"] = "public"
  if "_export" not in d: d["_export"] = "yes"

def getMetadata (identifier, user=ezidapp.models.AnonymousUser):
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
  """
  if identifier.startswith("doi:"):
    doi = util.validateDoi(identifier[4:])
    if not doi: return "error: bad request - invalid DOI identifier"
    ark = util.doi2shadow(doi)
    nqidentifier = "doi:" + doi
  elif identifier.startswith("ark:/"):
    ark = util.validateArk(identifier[5:])
    if not ark: return "error: bad request - invalid ARK identifier"
    nqidentifier = "ark:/" + ark
  elif identifier.startswith("urn:uuid:"):
    urn = util.validateUrnUuid(identifier[9:])
    if not urn: return "error: bad request - invalid UUID URN identifier"
    ark = util.urnUuid2shadow(urn)
    nqidentifier = "urn:uuid:" + urn
  else:
    return "error: bad request - unrecognized identifier scheme"
  tid = uuid.uuid1()
  if not _acquireIdentifierLock(ark, user.username):
    return "error: concurrency limit exceeded"
  try:
    log.begin(tid, "getMetadata", nqidentifier, user.username, user.pid,
      user.group.groupname, user.group.pid)
    d = _getElements(ark)
    if d is None:
      log.badRequest(tid)
      return "error: bad request - no such identifier"
    if not policy.authorizeView(user, nqidentifier, d):
      log.forbidden(tid)
      return "error: forbidden"
    # TRANSITION BEGIN
    if "_s" in d:
      d["_t"] = d["_st"]
      if "_st1" in d: d["_t1"] = d["_st1"]
      d["_u"] = d["_su"]
    # TRANSITION END
    convertMetadataDictionary(d, ark, nqidentifier.startswith("ark:/"))
    log.success(tid)
    return ("success: " + nqidentifier, d)
  except Exception, e:
    log.error(tid, e)
    return "error: internal server error"
  finally:
    _releaseIdentifierLock(ark, user.username)

def _fixupNonPublicTargets (d):
  if "_t" in d:
    d["_t1"] = d["_t"]
    del d["_t"]
  if "_st" in d:
    d["_st1"] = d["_st"]
    del d["_st"]

def setMetadata (identifier, user, metadata, updateExternalServices=True):
  """
  Sets metadata elements of a given qualified identifier, e.g.,
  "doi:10.5060/FOO".  'user' is the requestor and should be an
  authenticated StoreUser object.  'metadata' should be a dictionary
  of element (name, value) pairs.  If an element being set already
  exists, it is overwritten, if not, it is created; existing elements
  not set are left unchanged.  Of the reserved metadata elements, only
  "_target", "_profile", "_status", and "_export" may be set (unless
  the user is the EZID administrator, in which case the other reserved
  metadata elements may be set using their stored forms).  The
  "_crossref" element may be set only in certain situations.  The
  successful return is a string that includes the canonical, qualified
  form of the identifier, as in:

    success: doi:10.5060/FOO

  Unsuccessful returns include the strings:

    error: forbidden
    error: bad request - subreason...
    error: internal server error
    error: concurrency limit exceeded
  """
  if identifier.startswith("doi:"):
    doi = util.validateDoi(identifier[4:])
    if not doi: return "error: bad request - invalid DOI identifier"
    ark = util.doi2shadow(doi)
    nqidentifier = "doi:" + doi
  elif identifier.startswith("ark:/"):
    ark = util.validateArk(identifier[5:])
    if not ark: return "error: bad request - invalid ARK identifier"
    nqidentifier = "ark:/" + ark
  elif identifier.startswith("urn:uuid:"):
    urn = util.validateUrnUuid(identifier[9:])
    if not urn: return "error: bad request - invalid UUID URN identifier"
    ark = util.urnUuid2shadow(urn)
    nqidentifier = "urn:uuid:" + urn
  else:
    return "error: bad request - unrecognized identifier scheme"
  # 'd' will be our delta dictionary, i.e., it will hold the updates
  # to be applied to 'm', the identifier's current metadata.
  d = metadata.copy()
  if "_external_updates" in d and user.isSuperuser:
    # Easter egg.
    updateExternalServices = (d["_external_updates"].lower() == "yes")
    del d["_external_updates"]
  r = _validateMetadata(nqidentifier, user, d)
  if type(r) is str: return "error: bad request - " + r
  tid = uuid.uuid1()
  if not _acquireIdentifierLock(ark, user.username):
    return "error: concurrency limit exceeded"
  try:
    log.begin(tid, "setMetadata", nqidentifier, user.username, user.pid,
      user.group.groupname, user.group.pid,
      *[a for p in metadata.items() for a in p])
    m = _getElements(ark)
    if m is None:
      log.badRequest(tid)
      return "error: bad request - no such identifier"
    iUser = m["_o"]
    iGroup = m["_g"]
    if "_co" in m:
      # Semicolons are not valid characters in ARK identifiers.
      iCoOwners = [co.strip() for co in m["_co"].split(";")\
        if len(co.strip()) > 0]
    else:
      iCoOwners = []
    if not policy.authorizeUpdate(user, nqidentifier, iUser, iGroup):
      log.forbidden(tid)
      return "error: forbidden"
    if "_o" in d:
      if not policy.authorizeOwnershipChange(user, nqidentifier, iUser,
        d["_o"]):
        log.badRequest(tid)
        return "error: bad request - ownership change prohibited"
    # Deal with any status change first; subsequent processing will
    # then be performed according to the updated status.
    iStatus = m.get("_is", "public")
    if "_is" in d:
      if d["_is"] == "reserved":
        if iStatus != "reserved":
          log.badRequest(tid)
          return "error: bad request - invalid identifier status change"
        del d["_is"]
        _fixupNonPublicTargets(d)
      elif d["_is"] == "public":
        if iStatus == "public":
          del d["_is"]
        else:
          _softUpdate(d, { "_t": m["_t1"] })
          d["_t1"] = ""
          if "_st1" in m:
            _softUpdate(d, { "_st": m["_st1"] })
            d["_st1"] = ""
          d["_is"] = ""
      elif d["_is"].startswith("unavailable"):
        if iStatus.startswith("unavailable"):
          if d["_is"] == iStatus: del d["_is"]
          _fixupNonPublicTargets(d)
        elif iStatus == "public":
          d["_t1"] = d.get("_t", m["_t"])
          d["_t"] = _tombstoneTarget("ark:/" + ark)
          if "_s" in m:
            d["_st1"] = d.get("_st", m["_st"])
            d["_st"] = _tombstoneTarget(m["_s"])
        else:
          log.badRequest(tid)
          return "error: bad request - invalid identifier status change"
      else:
        assert False, "unhandled case"
    else:
      if iStatus != "public": _fixupNonPublicTargets(d)
    newStatus = d.get("_is", iStatus)
    if newStatus == "": newStatus = "public"
    # Update time.
    if nqidentifier.startswith("ark:/"):
      _softUpdate(d, { "_u": str(int(time.time())) })
    else:
      _softUpdate(d, { "_su": str(int(time.time())) })
    # Export flag.
    if d.get("_x", "") == "yes": d["_x"] = ""
    iExport = m.get("_x", "yes")
    newExport = d.get("_x", iExport)
    if newExport == "": newExport = "yes"
    # Crossref flag.
    if "_cr" in d:
      if d["_cr"] == "no":
        if newStatus != "reserved":
          log.badRequest(tid)
          return "error: bad request - Crossref registration can be " +\
            "removed only from reserved identifiers"
        d["_cr"] = ""
      else:
        # The new value might be "yes", or it might be a computed value.
        if "_cr" in m:
          if d["_cr"] == "yes": del d["_cr"]
        else:
          if not policy.authorizeCrossref(user, nqidentifier):
            # Technically it's an authorization error, but it makes more
            # sense to clients to receive a bad request.
            log.badRequest(tid)
            return "error: bad request - Crossref registration is not " +\
              "enabled for user and shoulder"
          if newStatus == "reserved":
            d["_cr"] = "yes | awaiting status change to public"
          else:
            d["_cr"] = "yes | registration in progress"
    else:
      if "_cr" in m and newStatus != "reserved":
        # The update will trigger a Crossref update.
        d["_cr"] = "yes | registration in progress"
    # Easter egg: a careful reading of the above shows that it is
    # impossible for the administrator to set certain internal
    # elements in certain cases.  To preserve the administrator's
    # ability to set *any* metadata, we include the totally
    # undocumented ability below.
    if user.isSuperuser:
      for k in d.keys():
        if k.startswith("_") and k.endswith("!"):
          d[k[:-1]] = d[k]
          del d[k]
    # Crossref-related requirements.
    if (("_cr" in d and d["_cr"].startswith("yes")) or\
      ("_cr" not in d and "_cr" in m)):
      if newExport != "yes":
        log.badRequest(tid)
        return "error: bad request - identifier registered with Crossref " +\
          "must be exported"
      if newStatus != "reserved" and not (("crossref" in d and\
        d["crossref"].strip() != "") or ("crossref" not in d and\
        "crossref" in m)):
        return "error: bad request - Crossref registration requires " +\
          "'crossref' deposit metadata"
    if "_s" in m and m["_s"].startswith("doi:"):
      # If the identifier is a DOI with Crossref metadata, make sure
      # the embedded identifier and target URL sections are
      # up-to-date, but only if the identifier is not reserved.
      # Unfortunately, doing this with the current code architecture
      # requires that the metadata be re-parsed and re-serialized.
      crm = d.get("crossref", m.get("crossref", "")).strip()
      if crm != "" and newStatus != "reserved" and (iStatus == "reserved" or
        "crossref" in d or "_st" in d):
        d["crossref"] = crossref.replaceTbas(crm, m["_s"][4:],
          d.get("_st", m["_st"]))
    # TRANSITION BEGIN
    if "_s" in m:
      if "_st" in d:
        d["_t"] = d["_st"]
      elif "_t" in d:
        if d["_t"] == _defaultTarget("ark:/" + ark):
          d["_st"] = d["_t"] = _defaultTarget(m["_s"])
        else:
          d["_st"] = d["_t"]
      if "_st1" in d:
        d["_t1"] = d["_st1"]
      elif "_t1" in d:
        if d["_t1"] == _defaultTarget("ark:/" + ark):
          d["_st1"] = d["_t1"] = _defaultTarget(m["_s"])
        else:
          d["_st1"] = d["_t1"]
      if "_su" in d:
        d["_u"] = d["_su"]
      elif "_u" in d:
        d["_su"] = d["_u"]
    # TRANSITION END
    # DataCite-related validations.  If it seems odd to be validating
    # way down here, it is... but we can't check metadata requirements
    # compliance without a complete picture of the metadata.
    m.update(d)
    r = _validateDatacite(nqidentifier, m, newStatus != "reserved")
    if type(r) is str:
      log.badRequest(tid)
      return "error: bad request - " + r
    # Propagate changes back to the delta dictionary (ugh).
    if "datacite.resourcetype" in d:
      d["datacite.resourcetype"] = m["datacite.resourcetype"]
    if "datacite" in d: d["datacite"] = m["datacite"]
    # Finally, and most importantly, update our own databases.
    noid_egg.setElements(ark, d)
    log.progress(tid, "noid_egg.setElements")
    store.update(ark, m, updateExternalServices=updateExternalServices)
  except Exception, e:
    log.error(tid, e)
    return "error: internal server error"
  else:
    log.success(tid)
    return "success: " + nqidentifier
  finally:
    _releaseIdentifierLock(ark, user.username)

def deleteIdentifier (identifier, user):
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
  if identifier.startswith("doi:"):
    doi = util.validateDoi(identifier[4:])
    if not doi: return "error: bad request - invalid DOI identifier"
    ark = util.doi2shadow(doi)
    nqidentifier = "doi:" + doi
  elif identifier.startswith("ark:/"):
    ark = util.validateArk(identifier[5:])
    if not ark: return "error: bad request - invalid ARK identifier"
    nqidentifier = "ark:/" + ark
  elif identifier.startswith("urn:uuid:"):
    urn = util.validateUrnUuid(identifier[9:])
    if not urn: return "error: bad request - invalid UUID URN identifier"
    ark = util.urnUuid2shadow(urn)
    nqidentifier = "urn:uuid:" + urn
  else:
    return "error: bad request - unrecognized identifier scheme"
  tid = uuid.uuid1()
  if not _acquireIdentifierLock(ark, user.username):
    return "error: concurrency limit exceeded"
  try:
    log.begin(tid, "deleteIdentifier", nqidentifier, user.username, user.pid,
      user.group.groupname, user.group.pid)
    m = _getElements(ark)
    if m is None:
      log.badRequest(tid)
      return "error: bad request - no such identifier"
    iUser = m["_o"]
    iGroup = m["_g"]
    if not policy.authorizeDelete(user, nqidentifier, m["_o"], m["_g"]):
      log.forbidden(tid)
      return "error: forbidden"
    if m.get("_is", "public") != "reserved":
      if not user.isSuperuser:
        log.badRequest(tid)
        return "error: bad request - identifier status does not support " +\
          "deletion"
    noid_egg.deleteIdentifier(ark)
    log.progress(tid, "noid_egg.deleteIdentifier")
    store.delete(ark)
  except Exception, e:
    log.error(tid, e)
    return "error: internal server error"
  else:
    log.success(tid)
    return "success: " + nqidentifier
  finally:
    _releaseIdentifierLock(ark, user.username)

def asAdmin (function, *args):
  """
  Calls 'function' defined in this module (e.g., ezid.setMetadata)
  with the given arguments, using EZID administrator credentials.  The
  given arguments should omit the 'user' argument the function
  nominally accepts.
  """
  if function == mintDoi:
    return mintDoi(args[0], ezidapp.models.getAdminUser(), *args[1:])
  elif function == createDoi:
    return createDoi(args[0], ezidapp.models.getAdminUser(), *args[1:])
  elif function == mintArk:
    return mintArk(args[0], ezidapp.models.getAdminUser(), *args[1:])
  elif function == createArk:
    return createArk(args[0], ezidapp.models.getAdminUser(), *args[1:])
  elif function == mintUrnUuid:
    return mintUrnUuid(ezidapp.models.getAdminUser(), *args)
  elif function == createUrnUuid:
    return createUrnUuid(args[0], ezidapp.models.getAdminUser(), *args[1:])
  elif function == mintIdentifier:
    return mintIdentifier(args[0], ezidapp.models.getAdminUser(), *args[1:])
  elif function == createIdentifier:
    return createIdentifier(args[0], ezidapp.models.getAdminUser(), *args[1:])
  elif function == getMetadata:
    return getMetadata(args[0], ezidapp.models.getAdminUser())
  elif function == setMetadata:
    return setMetadata(args[0], ezidapp.models.getAdminUser(), *args[1:])
  elif function == deleteIdentifier:
    return deleteIdentifier(args[0], ezidapp.models.getAdminUser())
  else:
    assert False, "unhandled case"
