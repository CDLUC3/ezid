# =============================================================================
#
# EZID :: stats.py
#
# Identifier statistics.
#
# To avoid burdening online identifier processing, statistics are
# computed periodically by a daemon thread.  We eschew a synchronous,
# inline approach to maintaining statistics because identifier changes
# can be complex (creation times can change, ownership can change,
# even users and groups can change) and tracking the effects of those
# changes on statistics would require knowledge of an identifier's
# pre-change state, which is not recorded.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2017, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import datetime
import django.db
import django.db.transaction
import threading
import time
import uuid

import config
import ezidapp.models
import log

_enabled = None
_computeCycle = None
_computeSameTimeOfDay = None
_threadName = None

def _sameTimeOfDayDelta ():
  now = datetime.datetime.now()
  midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
  d = _computeCycle - (now-midnight).total_seconds()
  if d < 0: d += 86400
  return d

def _timestampToMonth (t):
  return time.strftime("%Y-%m", time.localtime(t))

def _identifierType (id):
  return id.split(":")[0].upper()

def _statisticsDaemon ():
  if _computeSameTimeOfDay:
    django.db.connections["default"].close()
    django.db.connections["search"].close()
    time.sleep(_sameTimeOfDayDelta())
  else:
    # We arbitrarily sleep 10 minutes to avoid putting a burden on the
    # server near startup or reload.
    time.sleep(600)
  while _enabled and threading.currentThread().getName() == _threadName:
    start = time.time()
    try:
      users = { u.id: (u.pid, u.group.pid, u.realm.name) for u in\
        ezidapp.models.SearchUser.objects.all().select_related("group",
        "realm") }
      counts = {}
      lastIdentifier = ""
      while True:
        qs = ezidapp.models.SearchIdentifier.objects.filter(
          identifier__gt=lastIdentifier).only("identifier", "owner_id",
          "createTime", "isTest", "hasMetadata").order_by("identifier")
        qs = list(qs[:1000])
        if len(qs) == 0: break
        for id in qs:
          if not id.isTest and id.owner_id in users:
            t = (_timestampToMonth(id.createTime), id.owner_id,
              _identifierType(id.identifier), id.hasMetadata)
            counts[t] = counts.get(t, 0) + 1
        lastIdentifier = qs[-1].identifier
      with django.db.transaction.atomic():
        ezidapp.models.Statistics.objects.all().delete()
        for t, v in counts.items():
          c = ezidapp.models.Statistics(month=t[0], owner=users[t[1]][0],
            ownergroup=users[t[1]][1], realm=users[t[1]][2], type=t[2],
            hasMetadata=t[3], count=v)
          c.full_clean(validate_unique=False)
          c.save(force_insert=True)
    except Exception, e:
      log.otherError("stats._statisticsDaemon", e)
    # Since we're going to be sleeping for potentially a long time,
    # release any memory held.
    users = u = counts = lastIdentifier = qs = id = t = v = c = None
    django.db.connections["default"].close()
    django.db.connections["search"].close()
    if _computeSameTimeOfDay:
      time.sleep(_sameTimeOfDayDelta())
    else:
      time.sleep(max(_computeCycle-(time.time()-start), 0))

def _loadConfig ():
  global _enabled, _computeCycle, _computeSameTimeOfDay, _threadName
  _enabled = django.conf.settings.DAEMON_THREADS_ENABLED and\
    config.get("daemons.statistics_enabled").lower() == "true"
  if _enabled:
    _computeCycle = int(config.get("daemons.statistics_compute_cycle"))
    _computeSameTimeOfDay =\
      (config.get("daemons.statistics_compute_same_time_of_day").lower() ==\
      "true")
    _threadName = uuid.uuid1().hex
    t = threading.Thread(target=_statisticsDaemon, name=_threadName)
    t.setDaemon(True)
    t.start()

_loadConfig()
config.registerReloadListener(_loadConfig)
