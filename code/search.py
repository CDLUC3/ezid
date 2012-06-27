# =============================================================================
#
# EZID :: search.py
#
# Support for searching and browsing over identifier metadata.
#
# Note that the functions in this module are designed to hide errors
# from the caller by always returning successfully (but errors are
# still logged).
#
# Regarding concurrency, our preference would be that a thread
# requesting a lock wait (forever) until the lock is granted.
# However, it is well nigh impossible to defeat SQLite's default
# behavior, which is to raise an exception if the lock isn't obtained
# within a "timely" period (by default, 5 seconds).  For example, even
# a simple SELECT statement can timeout if a concurrent COMMIT is
# taking too long.  Our less-than-ideal strategy is to automatically
# re-issue requests at two key points only: when beginning a
# transaction (when a RESERVED lock is requested, and the thread has
# to wait until all other RESERVED and higher locks are released) and
# when committing a transaction (when a PENDING lock is requested, and
# the thread has to wait until all SHARED locks are released before
# the thread can advance to an EXCLUSIVE lock).  See
# <http://sqlite.org/lockingv3.html>.
#
# N.B.: it is important that cursors be closed (and closed as quickly
# as possible), as they represent SHARED locks.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2012, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import re
import sqlite3
import threading
import uuid

import config
import ezidadmin
import idmap
import log
import mapping

_dbLock = threading.Lock()
_cacheLock = threading.Lock()
_searchDatabase = None
_ldapEnabled = None
_coOwnershipMap = None

# Database connection pool.  We currently don't control or constrain
# the size of the pool.  The pool is identified by a UUID; when EZID
# is reloaded, the pool is emptied and given a new UUID.  Any
# outstanding connections drawn from the old pool are not returned to
# the new pool, but are simply closed when returned.
_pool = None
_poolId = None
_numConnections = None

def _loadConfig ():
  global _searchDatabase, _ldapEnabled, _coOwnershipMap, _pool, _poolId
  global _numConnections
  _ldapEnabled = (config.config("ldap.enabled").lower() == "true")
  _cacheLock.acquire()
  try:
    _coOwnershipMap = None
  finally:
    _cacheLock.release()
  _dbLock.acquire()
  try:
    _searchDatabase = config.config("DEFAULT.search_database")
    _pool = []
    _poolId = uuid.uuid1()
    _numConnections = 0
  finally:
    _dbLock.release()

_loadConfig()
config.addLoader(_loadConfig)

def setDatabase (file):
  """
  Sets the search database file.  This function is intended to be used
  by offline scripts only.  It must be called before any connections
  have been opened.
  """
  global _searchDatabase
  _searchDatabase = file

def _getConnection ():
  global _numConnections
  _dbLock.acquire()
  try:
    if len(_pool) > 0:
      return (_pool.pop(), _poolId)
    else:
      # Turn on auto-commit, so that a BEGIN statement can disable it
      # (sounds paradoxical, but that's how SQLite works).
      # Setting check_same_thread to false allows connections to be
      # used by different threads.  The almost nonexistent
      # documentation on this flag is confusing.  Either the check
      # enabled by this flag is not necessary at all, given the
      # version of SQLite we're using (3.7), or it's not necessary
      # given our thread/connection controls (which ensure that a
      # connection is used by only one thread at a time, and a
      # connection is returned to the pool only if and when no
      # transaction is in progress).
      c = sqlite3.connect(_searchDatabase, isolation_level=None,
        check_same_thread=False, timeout=30)
      _numConnections += 1
      return (c, _poolId)
  finally:
    _dbLock.release()

def _returnConnection (c, poolId, tainted=False):
  global _numConnections
  _dbLock.acquire()
  try:
    if poolId == _poolId:
      if tainted:
        _numConnections -= 1
        closeConnection = True
      else:
        _pool.append(c)
        closeConnection = False
    else:
      closeConnection = True
  finally:
    _dbLock.release()
  if closeConnection:
    try:
      c.close()
    except:
      pass

def numConnections ():
  """
  Returns the number of open database connections.
  """
  return _numConnections

def _begin (cursor):
  while True:
    try:
      # We choose this isolation level to avoid data manipulation
      # statements bombing out mid-transaction.
      cursor.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError, e:
      if e.message != "database is locked": raise e
    else:
      return True

def _commit (cursor):
  while True:
    try:
      cursor.execute("COMMIT")
    except sqlite3.OperationalError, e:
      if e.message != "database is locked": raise e
    else:
      break

def _rollback (cursor):
  try:
    cursor.execute("ROLLBACK")
  except sqlite3.DatabaseError, e:
    log.otherError("search._rollback", e)
    return False
  else:
    return True

def _closeCursor (cursor):
  try:
    cursor.close()
  except sqlite3.DatabaseError, e:
    log.otherError("search._closeCursor", e)
    return False
  else:
    return True

def _loadCoOwnershipLdap ():
  try:
    d = {}
    l = ezidadmin.getUsers()
    assert type(l) is list, "ezidadmin.getUsers failed: " + l
    for u, col in [(r["arkId"], r["ezidCoOwners"]) for r in l]:
      for co in re.split("[, ]+", col):
        if len(co) == 0: continue
        co = idmap.getUserId(co)
        if co not in d: d[co] = []
        if u not in d[co]: d[co].append(u)
    return d
  except Exception, e:
    log.otherError("search._loadCoOwnershipLdap", e)
    return {}

def _loadCoOwnershipLocal ():
  d = {}
  for u in config.config("users.keys").split(","):
    uId = config.config("user_%s.id" % u)
    for co in config.config("user_%s.co_owners" % u).split(","):
      if len(co) == 0: continue
      coId = config.config("user_%s.id" % co)
      if coId not in d: d[coId] = []
      if uId not in d[coId]: d[coId].append(uId)
  return d

def _getCoOwnership (user):
  global _coOwnershipMap
  _cacheLock.acquire()
  try:
    if _coOwnershipMap is None:
      if _ldapEnabled:
        _coOwnershipMap = _loadCoOwnershipLdap()
      else:
        _coOwnershipMap = _loadCoOwnershipLocal()
    return _coOwnershipMap.get(user, [])
  finally:
    _cacheLock.release()

def clearCoOwnershipCache ():
  """
  Clears the co-ownership cache.
  """
  global _coOwnershipMap
  _cacheLock.acquire()
  try:
    _coOwnershipMap = None
  finally:
    _cacheLock.release()

def _get (d, *keys):
  for k in keys:
    if k in d:
      if d[k] != "":
        return d[k]
      else:
        return None
  return None

_columns = ["identifier", "owner", "coOwners", "createTime", "updateTime",
  "status", "mappedTitle", "mappedCreator"]

def _processMetadata (identifier, metadata, mapLocalNames):
  m = {}
  m["identifier"] = identifier
  m["owner"] = _get(metadata, "_owner", "_o")
  assert m["owner"] is not None, "missing required metadata element"
  if mapLocalNames: m["owner"] = idmap.getUserId(m["owner"])
  m["coOwners"] = _get(metadata, "_coowners", "_co")
  if mapLocalNames and m["coOwners"] is not None:
    m["coOwners"] = " ; ".join(idmap.getUserId(co.strip())\
      for co in m["coOwners"].split(";") if len(co.strip()) > 0)
  createTime = _get(metadata, "_created", "_c")
  assert createTime is not None, "missing required metadata element"
  m["createTime"] = int(createTime)
  updateTime = _get(metadata, "_updated", "_su", "_u")
  assert updateTime is not None, "missing required metadata element"
  m["updateTime"] = int(updateTime)
  m["status"] = _get(metadata, "_status", "_is")
  if m["status"] is None: m["status"] = "public"
  creator, title, publisher, date = mapping.getDisplayMetadata(metadata)
  m["mappedTitle"] = title
  m["mappedCreator"] = creator
  return m

def _rowTupleToDict (row):
  m = {}
  for i in range(len(_columns)): m[_columns[i]] = row[i]
  return m

def _insert (identifier, m, cursor):
  cursor.execute("INSERT INTO identifier (%s) VALUES (%s)" %\
    (", ".join(_columns), ", ".join(["?"]*len(_columns))),
    tuple(m[k] for k in _columns))
  ownerList = [m["owner"]]
  if m["coOwners"] is not None:
    ownerList.extend(co.strip() for co in m["coOwners"].split(";")\
      if len(co.strip()) > 0)
  for o in ownerList:
    cursor.execute("INSERT INTO ownership (owner, identifier) VALUES (?, ?)",
      (o, identifier))

def insert (identifier, metadata, mapLocalNames=False):
  """
  Inserts an identifier in the search database.  'metadata' should be
  a dictionary of element (name, value) pairs.  Element names may be
  given in stored (_o, _t/_st, etc.) or transmitted (_owner, _target,
  etc.) forms.  Elements _owner, _created, and _updated must be
  present.  If mapLocalNames is true, agent names are assumed to be in
  local form and are mapped to ARK identifiers as required by the
  search database schema.
  """
  m = _processMetadata(identifier, metadata, mapLocalNames)
  connection = None
  tainted = False
  c = None
  begun = False
  try:
    connection, poolId = _getConnection()
    c = connection.cursor()
    begun = _begin(c)
    _insert(identifier, m, c)
    _commit(c)
  except Exception, e:
    log.otherError("search.insert", e)
    if begun:
      if not _rollback(c): tainted = True
  finally:
    if c:
      if not _closeCursor(c): tainted = True
    if connection: _returnConnection(connection, poolId, tainted)

def update (identifier, metadata, insertIfNecessary=False,
  mapLocalNames=False):
  """
  Updates an identifier in the search database.  The identifier must
  already exist in the database unless insertIfNecessary is true, in
  which case the identifier is inserted if necessary.  'metadata'
  should be a dictionary of element (name, value) pairs.  Element
  names may be given in stored (_o, _t/_st, etc.) or transmitted
  (_owner, _target, etc.) forms.  Elements _owner, _created, and
  _updated must be present.  If mapLocalNames is true, agent names are
  assumed to be in local form and are mapped to ARK identifiers as
  required by the search database schema.
  """
  m = _processMetadata(identifier, metadata, mapLocalNames)
  connection = None
  tainted = False
  c = None
  begun = False
  try:
    connection, poolId = _getConnection()
    c = connection.cursor()
    begun = _begin(c)
    c.execute("SELECT %s FROM identifier WHERE identifier = ?" %\
      ", ".join(_columns), (identifier,))
    r = c.fetchone()
    if insertIfNecessary:
      if r is None:
        _insert(identifier, m, c)
        _commit(c)
        return
    else:
      assert r is not None, "no such identifier in search database: " +\
        identifier
    r = _rowTupleToDict(r)
    for k in _columns:
      if m[k] == r[k]: del m[k]
    if len(m) > 0:
      keys = m.keys()
      c.execute("UPDATE identifier SET %s WHERE identifier = ?" %\
        ", ".join("%s = ?" % k for k in keys),
        tuple([m[k] for k in keys] + [identifier]))
      if "owner" in keys:
        c.execute("DELETE FROM ownership WHERE owner = ? AND " +\
          "identifier = ?", (r["owner"], identifier))
        c.execute("INSERT INTO ownership (owner, identifier) VALUES (?, ?)",
          (m["owner"], identifier))
      if "coOwners" in keys:
        rCoOwners = [co.strip() for co in (r["coOwners"] or "").split(";")\
          if len(co.strip()) > 0]
        mCoOwners = [co.strip() for co in (m["coOwners"] or "").split(";")\
          if len(co.strip()) > 0]
        for co in rCoOwners:
          if co not in mCoOwners:
            c.execute("DELETE FROM ownership WHERE owner = ? AND " +\
              "identifier = ?", (co, identifier))
        for co in mCoOwners:
          if co not in rCoOwners:
            c.execute("INSERT INTO ownership (owner, identifier) " +\
              "VALUES (?, ?)", (co, identifier))
    _commit(c)
  except Exception, e:
    log.otherError("search.update", e)
    if begun:
      if not _rollback(c): tainted = True
  finally:
    if c:
      if not _closeCursor(c): tainted = True
    if connection: _returnConnection(connection, poolId, tainted)

def getByOwner (owner, includeCoOwnership=True, sortColumn="updateTime",
  ascending=False, limit=-1, offset=0, useLocalNames=True):
  """
  Returns all identifiers belonging to an EZID user.  'owner' should
  be the user's local name (e.g., "dryad") if 'useLocalNames' is true
  or persistent identifier (e.g., "ark:/99166/p92z12p14") otherwise.
  The return is a list of dictionaries keyed by column name.  If
  'useLocalNames' is true, returned agents are mapped to local names.
  If 'includeCoOwnership' is false, only identifiers directly owned by
  'owner' are returned; if true, identifiers owned by 'owner' by
  virtue of co-ownership (identifier-level and account-level) are
  included as well.  'sortColumn' and 'ascending' define the ordering
  of the results.  'limit' and 'offset' have the usual SQL semantics.
  """
  assert sortColumn in _columns, "invalid sort column"
  if useLocalNames: owner = idmap.getUserId(owner)
  if includeCoOwnership:
    col = _getCoOwnership(owner)
    q = ("SELECT %s%s FROM identifier A, ownership B ON " +\
      "A.identifier = B.identifier WHERE B.owner = ?%s ORDER BY A.%s %s " +\
      "LIMIT %d OFFSET %d") %\
      ("DISTINCT " if len(col) > 0 else "",
      ", ".join("A." + c for c in _columns),
      " OR B.owner = ?"*len(col),
      sortColumn, "ASC" if ascending else "DESC", limit, offset)
    p = tuple([owner] + col)
  else:
    q = ("SELECT %s FROM identifier WHERE owner = ? ORDER BY %s %s " +\
      "LIMIT %d OFFSET %d") %\
      (", ".join(_columns),
      sortColumn, "ASC" if ascending else "DESC", limit, offset)
    p = (owner,)
  connection = None
  tainted = False
  c = None
  try:
    connection, poolId = _getConnection()
    c = connection.cursor()
    c.execute(q, p)
    r = []
    for row in c:
      m = _rowTupleToDict(row)
      if useLocalNames:
        m["owner"] = idmap.getAgent(m["owner"])[0]
        if m["coOwners"] is not None:
          m["coOwners"] = " ; ".join(idmap.getAgent(co.strip())[0]\
            for co in m["coOwners"].split(";") if len(co.strip()) > 0)
      r.append(m)
    return r
  except Exception, e:
    log.otherError("search.getByOwner", e)
    return []
  finally:
    if c:
      if not _closeCursor(c): tainted = True
    if connection: _returnConnection(connection, poolId, tainted)

def getByOwnerCount (owner, includeCoOwnership=True, useLocalNames=True):
  """
  Returns the total number of identifiers that would be returned by a
  comparable, limit-less call to getByOwner.
  """
  if useLocalNames: owner = idmap.getUserId(owner)
  if includeCoOwnership:
    col = _getCoOwnership(owner)
    q = "SELECT COUNT(%sidentifier) FROM ownership WHERE owner = ?%s" %\
      ("DISTINCT " if len(col) > 0 else "",
      " OR owner = ?"*len(col))
    p = tuple([owner] + col)
  else:
    q = "SELECT COUNT(*) FROM identifier WHERE owner = ?"
    p = (owner,)
  connection = None
  tainted = False
  c = None
  try:
    connection, poolId = _getConnection()
    c = connection.cursor()
    c.execute(q, p)
    return c.fetchone()[0]
  except Exception, e:
    log.otherError("search.getByOwnerCount", e)
    return 0
  finally:
    if c:
      if not _closeCursor(c): tainted = True
    if connection: _returnConnection(connection, poolId, tainted)

def delete (identifier):
  """
  Deletes an identifier from the search database.
  """
  connection = None
  tainted = False
  c = None
  begun = False
  try:
    connection, poolId = _getConnection()
    c = connection.cursor()
    begun = _begin(c)
    c.execute("DELETE FROM ownership WHERE identifier = ?", (identifier,))
    c.execute("DELETE FROM identifier WHERE identifier = ?", (identifier,))
    _commit(c)
  except Exception, e:
    log.otherError("search.delete", e)
    if begun:
      if not _rollback(c): tainted = True
  finally:
    if c:
      if not _closeCursor(c): tainted = True
    if connection: _returnConnection(connection, poolId, tainted)
