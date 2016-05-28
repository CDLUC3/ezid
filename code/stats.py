# =============================================================================
#
# EZID :: stats.py
#
# Identifier statistics.
#
# The computed statistics consist of a single, multi-dimensional
# histogram that counts identifiers as categorized across various
# dimensions.  This module is written to be independent of the actual
# dimensions (except for variable _defaultDimensions), but in fact the
# dimensions are:
#
#    name          description
#    -----------   -----------------------------------------------------
#    month         creation month (e.g., "2011-03")
#    owner         owner's ARK identifier (e.g., "ark:/99166/p92z12p14")
#    group         owning group's ARK identifier
#    type          identifier type (e.g, "ARK")
#    hasMetadata   "True" or "False"
#
# The histogram counts do not include test identifiers, but do include
# reserved identifiers.
#
# Note that the statistics are not live; they're computed by a
# background process and this module simply loads them.  If no
# statistics have been computed yet, an empty histogram is returned.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2012, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import errno
import os
import threading
import time

import config
import ezidapp.models
import log

_defaultDimensions = ["month", "owner", "group", "type", "hasMetadata"]
_lock = threading.Lock()
_statsFile = None
_statsFileMtime = None
_stats = None

def _loadConfig ():
  global _statsFile, _statsFileMtime
  _statsFile = config.get("DEFAULT.stats_file")
  _statsFileMtime = 0

_loadConfig()
config.registerReloadListener(_loadConfig)

def _loadStats ():
  global _statsFileMtime, _stats
  _lock.acquire()
  try:
    mtime = int(os.stat(_statsFile).st_mtime)
    if mtime != _statsFileMtime:
      f = open(_statsFile)
      computeTime = int(f.readline().strip())
      dimensions = f.readline().split()
      assert len(dimensions) > 0, "no dimensions in stats file"
      histogram = {}
      for l in f:
        ls = l.split()
        assert len(ls) == len(dimensions)+1, "tuple/dimensions mismatch"
        histogram[tuple(ls[:-1])] = int(ls[-1])
      f.close()
      _stats = Stats(computeTime, dimensions, histogram)
      _statsFileMtime = mtime
  except Exception, e:
    # It's OK if the stats file doesn't exist.
    if not (isinstance(e, OSError) and e.errno == errno.ENOENT):
      log.otherError("stats._loadStats", e)
    _stats = Stats(int(time.time()), _defaultDimensions, {})
  finally:
    _lock.release()

class Stats (object):
  """
  Holds a set of statistics.
  """
  def __init__ (self, computeTime, dimensions, histogram):
    self._computeTime = computeTime
    self._dimensions = dimensions
    self._histogram = histogram
    try:
      self._monthIndex = dimensions.index("month")
    except:
      self._monthIndex = -1
    try:
      self._ownerIndex = dimensions.index("owner")
    except:
      self._ownerIndex = -1
    try:
      self._groupIndex = dimensions.index("group")
    except:
      self._groupIndex = -1
  def getComputeTime (self):
    """
    Returns the time the statistics were computed, as a Unix
    timestamp.
    """
    return self._computeTime
  def getDimensions (self):
    """
    Returns the (names of the) dimensions of the histogram as a list.
    """
    return self._dimensions[:]
  def getDomainValues (self, dimension, useLocalNames=True):
    """
    Returns a list of the domain values for a given dimension that
    have nonzero counts.  If the dimension is "owner" or "group", and
    if useLocalNames is true, the domain values (which are ARK
    identifiers) are converted to local names.  The values are sorted.
    """
    i = self._dimensions.index(dimension)
    s = set()
    for t in self._histogram:
      if dimension == "owner" and useLocalNames:
        s.add(ezidapp.models.getUserByPid(t[i]).username)
      elif dimension == "group" and useLocalNames:
        s.add(ezidapp.models.getGroupByPid(t[i]).groupname)
      else:
        s.add(t[i])
    l = list(s)
    l.sort()
    return l
  def query (self, constraints, useLocalNames=True):
    """
    Returns the sum of a subset of the histogram counts.  The subset
    is specified by 'constraints', which may be a tuple or list, the
    length of which must match the number of dimensions.  Each tuple
    component, if not None, is interpreted as a constraint against the
    corresponding dimension.  Thus a tuple of all Nones represents no
    constraint at all (and the total number of identifiers is
    returned), while a tuple with no Nones returns a single histogram
    value.  If useLocalNames is true, agent identifiers in
    'constraints' are interpreted as local names and are converted to
    agent identifiers.
    """
    assert len(constraints) == len(self._dimensions)
    constraints = list(constraints)
    if useLocalNames:
      if self._ownerIndex >= 0 and constraints[self._ownerIndex] is not None:
        constraints[self._ownerIndex] =\
          ezidapp.models.getUserByUsername(constraints[self._ownerIndex]).pid
      if self._groupIndex >= 0 and constraints[self._groupIndex] is not None:
        constraints[self._groupIndex] =\
          ezidapp.models.getGroupByGroupname(constraints[self._groupIndex]).pid
    count = 0
    for t, c in self._histogram.items():
      include = True
      for i in range(len(constraints)):
        if constraints[i] is not None and t[i] != constraints[i]:
          include = False
          break
      if include: count += c
    return count
  def getTable (self, owner=None, group=None, realm=None, useLocalNames=True):
    """
    Returns a table (a list) of histogram counts ordered by month.
    Each element of the list is a pair consisting of a month and a
    dictionary; the latter maps histogram tuples (sans month, owner,
    and group) to counts.  For example:

      ("2016-01", { ("ARK", "False"): 14837, ("ARK", "True"): 1789,
        ("DOI", "False"): 173, ("DOI", "True"): 11267 })

    In dictionaries zero counts are not represented, and thus
    dictionaries will not necessarily be complete with respect to the
    Cartesian product of the histogram dimensions.  The range of
    months returned is determined by the range of nonzero counts, but
    within that range months are guaranteed to be consecutive.  Empty
    entries will resemble:

      ("2016-02", {})

    The table can optionally be limited by owner and/or group and/or
    realm.  If useLocalNames is True, 'owner' and 'group' are
    interpreted as local names and are converted to agent identifiers.
    'realm' should be given as a realm name, e.g., "CDL".
    """
    assert self._monthIndex >= 0, "no month dimension"
    excludeIndexes = [self._monthIndex]
    if owner is not None:
      assert self._ownerIndex >= 0, "no owner dimension"
      if useLocalNames: owner = ezidapp.models.getUserByUsername(owner).pid
    if group is not None:
      assert self._groupIndex >= 0, "no group dimension"
      if useLocalNames: group = ezidapp.models.getGroupByGroupname(group).pid
    if realm is not None:
      groups = set(g.pid for g in\
        ezidapp.models.StoreRealm.objects.get(name=realm).groups.all())
    if self._ownerIndex >= 0: excludeIndexes.append(self._ownerIndex)
    if self._groupIndex >= 0: excludeIndexes.append(self._groupIndex)
    includeIndexes = [i for i in range(len(_defaultDimensions))\
      if i not in excludeIndexes]
    counts = {}
    for t, c in self._histogram.items():
      if (owner is None or t[self._ownerIndex] == owner) and\
        (group is None or t[self._groupIndex] == group) and\
        (realm is None or t[self._groupIndex] in groups):
        tt = tuple(t[i] for i in includeIndexes)
        d = counts.get(t[self._monthIndex], {})
        dc = d.get(tt, 0)
        d[tt] = dc + c
        counts[t[self._monthIndex]] = d
    def incrementMonth (month):
      y, m = [int(c) for c in month.split("-")]
      m += 1
      if m > 12:
        m = 1
        y += 1
      return "%04d-%02d" % (y, m)
    table = []
    months = counts.keys()
    months.sort()
    for m in months:
      if m != months[0]:
        nextM = incrementMonth(lastM)
        while nextM != m:
          table.append((nextM, {}))
          nextM = incrementMonth(nextM)
      table.append((m, counts[m]))
      lastM = m
    return table

def getStats ():
  """
  Returns a Stats object holding the most recently computed
  statistics.
  """
  _loadStats()
  return _stats
