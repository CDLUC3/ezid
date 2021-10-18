
"""Daemon that periodically pulls link checker results into the main
EZID tables.
"""

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import abc
import logging
import threading
import time
import uuid

import django.conf
import django.db
import django.db.transaction

import ezidapp.management.commands.proc_base
import ezidapp.models.identifier
import ezidapp.models.link_checker

log = logging.getLogger(__name__)


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand, abc.ABC):
    help = __doc__
    display = 'LinkCheckerUpdate'
    name = 'linkcheckerupdate'
    setting = 'DAEMONS_LINKCHECK_UPDATE_ENABLED'

    def __init__(self):
        super(Command, self).__init__(__name__)

    def add_arguments(self, parser):
        super().add_arguments(parser)

    def handle_daemon(self, args):
        print(args)
        pass

    def _sameTimeOfDayDelta(self):
        now = self.now()()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # noinspection PyTypeChecker
        d = self._resultsUploadCycle - (now - midnight).total_seconds()
        if d < 0:
            d += 86400
        return d

    def _harvest(self, model, only=None, filter=None):
        lastIdentifier = ""
        while True:
            qs = model.objects.filter(identifier__gt=lastIdentifier).order_by(
                "identifier"
            )
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

    def _linkcheckUpdateDaemon(self):
        if self._resultsUploadSameTimeOfDay:
            django.db.connections["search"].close()
            time.sleep(self._sameTimeOfDayDelta())
        else:
            # We arbitrarily sleep 10 minutes to avoid putting a burden on the
            # server near startup or reload.
            time.sleep(600)
        while (
            django.conf.settings.CROSSREF_ENABLED
            and threading.currentThread().getName() == self._threadName
        ):
            start = time.time()
            try:
                # noinspection PyTypeChecker
                siGenerator = self._harvest(
                    ezidapp.models.identifier.Identifier,
                    ["identifier", "linkIsBroken"],
                )
                # noinspection PyTypeChecker
                lcGenerator = self._harvest(
                    ezidapp.models.link_checker.LinkChecker,
                    ["identifier", "numFailures"],
                    lambda lc: lc.numFailures >= self._notificationThreshold,
                )
                si = next(siGenerator)
                lc = next(lcGenerator)
                while (
                    si is not None
                    and django.conf.settings.CROSSREF_ENABLED
                    and threading.currentThread().getName() == self._threadName
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
                        # Before updating the Identifier, we carefully lock
                        # the table and ensure that the object still exists.
                        try:
                            with django.db.transaction.atomic(using="search"):
                                si2 = ezidapp.models.identifier.Identifier.objects.get(
                                    identifier=si.identifier
                                )
                                si2.linkIsBroken = newValue
                                si2.computeHasIssues()
                                si2.save(update_fields=["linkIsBroken", "hasIssues"])
                        except ezidapp.models.identifier.Identifier.DoesNotExist:
                            log.exception(' ezidapp.models.identifier.Identifier.DoesNotExist')
                            pass
                    si = next(siGenerator)


            except Exception as e:
                log.exception(' Exception as e')
                self.otherError("linkcheck_update._linkcheckUpdateDaemon", e)
            # Since we're going to be sleeping for potentially a long time,
            # release any memory held.
            _siGenerator = _lcGenerator = _si = _lc = _si2 = None
            django.db.connections["search"].close()
            if self._resultsUploadSameTimeOfDay:
                time.sleep(self._sameTimeOfDayDelta())
            else:
                # noinspection PyTypeChecker
                time.sleep(max(self._resultsUploadCycle - (time.time() - start), 0))

    _resultsUploadCycle = None
    _resultsUploadSameTimeOfDay = None
    _notificationThreshold = None
    _threadName = None

    if django.conf.settings.CROSSREF_ENABLED:
        _resultsUploadCycle = django.conf.settings.LINKCHECKER_RESULTS_UPLOAD_CYCLE
        _resultsUploadSameTimeOfDay = (
            django.conf.settings.LINKCHECKER_RESULTS_UPLOAD_SAME_TIME_OF_DAY
        )
        _notificationThreshold = int(
            django.conf.settings.LINKCHECKER_NOTIFICATION_THRESHOLD
        )
        _threadName = uuid.uuid1().hex
        t = threading.Thread(target=_linkcheckUpdateDaemon, name=_threadName)
