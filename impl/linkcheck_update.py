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
import threading
import time
import uuid

import django.conf
import django.db
import django.db.transaction

import ezidapp.models.link_checker
import ezidapp.models.link_checker
import ezidapp.models.search_identifier
import ezidapp.models.search_identifier
import impl.config
import impl.log

_enabled = None
_resultsUploadCycle = None
_resultsUploadSameTimeOfDay = None
_notificationThreshold = None
_threadName = None


def _sameTimeOfDayDelta():
    now = datetime.datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # noinspection PyTypeChecker
    d = _resultsUploadCycle - (now - midnight).total_seconds()
    if d < 0:
        d += 86400
    return d


def _harvest(model, only=None, filter=None):
    lastIdentifier = ""
    while True:
        qs = model.objects.filter(identifier__gt=lastIdentifier).order_by("identifier")
        if only is not None:
            qs = qs.only(*only)
        qs = list(qs[:1000])
        if len(qs) == 0:
            break
        for o in qs:
            if filter is None or list(filter(o)):
                yield o
        lastIdentifier = qs[-1].identifier
    yield None


def _linkcheckUpdateDaemon():
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
            # noinspection PyTypeChecker
            siGenerator = _harvest(
                ezidapp.models.search_identifier.SearchIdentifier,
                ["identifier", "linkIsBroken"],
            )
            # noinspection PyTypeChecker
            lcGenerator = _harvest(
                ezidapp.models.link_checker.LinkChecker,
                ["identifier", "numFailures"],
                lambda lc: lc.numFailures >= _notificationThreshold,
            )
            si = next(siGenerator)
            lc = next(lcGenerator)
            while (
                si is not None
                and _enabled
                and threading.currentThread().getName() == _threadName
            ):
                while lc is not None and lc.identifier < si.identifier:
                    lc = next(lcGenerator)
                newValue = None
                if lc is None or lc.identifier > si.identifier:
                    if si.linkIsBroken:
                        newValue = False
                else:
                    if not si.linkIsBroken:
                        newValue = True
                    lc = next(lcGenerator)
                if newValue is not None:
                    # Before updating the SearchIdentifier, we carefully lock
                    # the table and ensure that the object still exists.
                    try:
                        with django.db.transaction.atomic(using="search"):
                            si2 = ezidapp.models.search_identifier.SearchIdentifier.objects.get(
                                identifier=si.identifier
                            )
                            si2.linkIsBroken = newValue
                            si2.computeHasIssues()
                            si2.save(update_fields=["linkIsBroken", "hasIssues"])
                    except ezidapp.models.search_identifier.SearchIdentifier.DoesNotExist:
                        pass
                si = next(siGenerator)
        except Exception as e:
            impl.log.otherError("linkcheck_update._linkcheckUpdateDaemon", e)
        # Since we're going to be sleeping for potentially a long time,
        # release any memory held.
        _siGenerator = _lcGenerator = _si = _lc = _si2 = None
        django.db.connections["search"].close()
        if _resultsUploadSameTimeOfDay:
            time.sleep(_sameTimeOfDayDelta())
        else:
            # noinspection PyTypeChecker
            time.sleep(max(_resultsUploadCycle - (time.time() - start), 0))


def loadConfig():
    global _enabled, _resultsUploadCycle, _resultsUploadSameTimeOfDay
    global _notificationThreshold, _threadName
    _enabled = (
        django.conf.settings.DAEMON_THREADS_ENABLED
        and impl.config.get("daemons.linkcheck_update_enabled").lower() == "true"
    )
    if _enabled:
        _resultsUploadCycle = int(impl.config.get("linkchecker.results_upload_cycle"))
        _resultsUploadSameTimeOfDay = (
            impl.config.get("linkchecker.results_upload_same_time_of_day").lower()
            == "true"
        )
        _notificationThreshold = int(
            impl.config.get("linkchecker.notification_threshold")
        )
        _threadName = uuid.uuid1().hex
        t = threading.Thread(target=_linkcheckUpdateDaemon, name=_threadName)
        t.setDaemon(True)
        t.start()
