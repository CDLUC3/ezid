# =============================================================================
#
# EZID :: linkcheck_update.py
#
# Daemon that periodically pulls link checker results into the main
# EZID tables.
#
# This module should be imported at server startup so that its daemon
# thread is started.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2016, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import datetime
import django.conf
import django.db
import django.db.transaction
import threading
import time
import uuid

import config
import ezidapp.models
import log

_enabled = None
_resultsUploadCycle = None
_resultsUploadSameTimeOfDay = None
_notificationThreshold = None
_threadName = None

def _sameTimeOfDayDelta ():
  now = datetime.datetime.now()
  midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
  d = _resultsUploadCycle - (now-midnight).total_seconds()
  if d < 0: d += 86400
  return d

def _harvest (model, only=None, filter=None):
  lastIdentifier = ""
  while True:
    qs = model.objects.filter(identifier__gt=lastIdentifier).order_by(
      "identifier")
    if only != None: qs = qs.only(*only)
    qs = list(qs[:1000])
    if len(qs) == 0: break
    for o in qs:
      if filter == None or filter(o): yield o
    lastIdentifier = qs[-1].identifier
  yield None

def _linkcheckUpdateDaemon ():
  if _resultsUploadSameTimeOfDay:
    django.db.connections["search"].close()
    time.sleep(_sameTimeOfDayDelta())
  else:
    # We arbitrarily sleep 10 minutes to avoid putting a burden on the
    # server near startup or reload.
    time.sleep(600)
  while _enabled and threading.currentThread().getName() == _threadName:
    start = time.time()
    try:
      siGenerator = _harvest(ezidapp.models.SearchIdentifier, ["identifier",
        "linkIsBroken"])
      lcGenerator = _harvest(ezidapp.models.LinkChecker, ["identifier",
        "numFailures"], lambda lc: lc.numFailures >= _notificationThreshold)
      si = siGenerator.next()
      lc = lcGenerator.next()
      while si != None and _enabled and\
        threading.currentThread().getName() == _threadName:
        while lc != None and lc.identifier < si.identifier:
          lc = lcGenerator.next()
        newValue = None
        if lc == None or lc.identifier > si.identifier:
          if si.linkIsBroken: newValue = False
        else:
          if not si.linkIsBroken: newValue = True
          lc = lcGenerator.next()
        if newValue != None:
          # Before updating the SearchIdentifier, we carefully lock
          # the table and ensure that the object still exists.
          try:
            with django.db.transaction.atomic():
              si2 = ezidapp.models.SearchIdentifier.objects.get(
                identifier=si.identifier)
              si2.linkIsBroken = newValue
              si2.computeHasIssues()
              si2.save(update_fields=["linkIsBroken", "hasIssues"])
          except ezidapp.models.SearchIdentifier.DoesNotExist:
            pass
        si = siGenerator.next()
    except Exception, e:
      log.otherError("linkcheck_update._linkcheckUpdateDaemon", e)
    django.db.connections["search"].close()
    if _resultsUploadSameTimeOfDay:
      time.sleep(_sameTimeOfDayDelta())
    else:
      time.sleep(max(_resultsUploadCycle-(time.time()-start), 0))

def _loadConfig ():
  global _enabled, _resultsUploadCycle, _resultsUploadSameTimeOfDay
  global _notificationThreshold, _threadName
  _enabled = django.conf.settings.DAEMON_THREADS_ENABLED and\
    config.get("daemons.linkcheck_update_enabled").lower() == "true"
  if _enabled:
    _resultsUploadCycle = int(config.get("linkchecker.results_upload_cycle"))
    _resultsUploadSameTimeOfDay = (config.get(
      "linkchecker.results_upload_same_time_of_day").lower() == "true")
    _notificationThreshold =\
      int(config.get("linkchecker.notification_threshold"))
    _threadName = uuid.uuid1().hex
    t = threading.Thread(target=_linkcheckUpdateDaemon, name=_threadName)
    t.setDaemon(True)
    t.start()

_loadConfig()
config.registerReloadListener(_loadConfig)
