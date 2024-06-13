#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Daemon that periodically pulls link checker results into the main
EZID tables.
"""

import datetime
import logging

import django.conf
import django.db
import django.db.transaction

import ezidapp.management.commands.proc_base
import ezidapp.models.identifier
import ezidapp.models.link_checker
import impl.log
from impl.open_search_doc import OpenSearchDoc
import opensearchpy.exceptions

log = logging.getLogger(__name__)


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    name = __name__
    setting = 'DAEMONS_LINKCHECK_UPDATE_ENABLED'
    # Number of records retrieved per database call in _harvest, 100000 seems ok
    # and balances time taken vs resource use

    def __init__(self):
        super().__init__()
        self.resultsUploadCycle = django.conf.settings.LINKCHECKER_RESULTS_UPLOAD_CYCLE
        self.resultsUploadSameTimeOfDay = (
            django.conf.settings.LINKCHECKER_RESULTS_UPLOAD_SAME_TIME_OF_DAY
        )
        self.notificationThreshold = django.conf.settings.LINKCHECKER_NOTIFICATION_THRESHOLD

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--pagesize', help='Rows in each database page (100,000)', type=int, default=100000
        )

    def run(self):
        if self.opt.pagesize <= 0:
            self.opt.pagesize = 1
        if not self.opt.debug:
            if self.resultsUploadSameTimeOfDay:
                self.sleep(self._sameTimeOfDayDelta())
            else:
                # We arbitrarily sleep 10 minutes to avoid putting a burden on the
                # server near startup or reload.
                self.sleep(600)

        while not self.terminated():
            start = self.now()
            try:
                # noinspection PyTypeChecker
                siGenerator = self._harvest(
                    ezidapp.models.identifier.SearchIdentifier,
                    ["identifier", "linkIsBroken"],
                )

                # Note: this call is extremely slow since the list is built by
                # iterating over everything...
                # noinspection PyTypeChecker
                lcGenerator = self._harvest(
                    ezidapp.models.link_checker.LinkChecker,
                    ["identifier", "numFailures"],
                    lambda lc: lc.numFailures >= self.notificationThreshold,
                )
                si = next(siGenerator)
                lc = next(lcGenerator)
                while si is not None:
                    log.debug("Processing %s", si.identifier)
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
                        log.debug("Updating %s", si.identifier)
                        # Before updating the Identifier, we carefully lock
                        # the table and ensure that the object still exists.
                        try:
                            with django.db.transaction.atomic():
                                si2 = ezidapp.models.identifier.SearchIdentifier.objects.get(
                                    identifier=si.identifier
                                )
                                si2.linkIsBroken = newValue
                                si2.computeHasIssues()
                                si2.save(update_fields=["linkIsBroken", "hasIssues"])
                                open_s = OpenSearchDoc(identifier=si2)
                                open_s.update_link_issues(link_is_broken=si2.linkIsBroken, has_issues=si2.hasIssues)
                        except ezidapp.models.identifier.SearchIdentifier.DoesNotExist:
                            log.exception('SearchIdentifier.DoesNotExist')
                        except opensearchpy.exceptions.OpenSearchException as e:
                            log.exception('OpenSearchException in link checker', e)

                    si = next(siGenerator)

            except Exception as e:
                log.exception('Exception')
                impl.log.otherError("linkcheck_update._linkcheckUpdateDaemon", e)

            siGenerator = lcGenerator = si = lc = si2 = None

            if self.resultsUploadSameTimeOfDay:
                self.sleep(self._sameTimeOfDayDelta())
            else:
                self.sleep(max(self.resultsUploadCycle - (self.now() - start), 0))

    def _sameTimeOfDayDelta(self):
        now = datetime.datetime.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        d = self.resultsUploadCycle - (now - midnight).total_seconds()
        if d < 0:
            d += 86400
        return d

    def _harvest(self, model, only=None, filter=None):
        lastIdentifier = ""
        while not self.terminated():
            qs = model.objects.filter(identifier__gt=lastIdentifier).order_by("identifier")
            if only is not None:
                qs = qs.only(*only)
            qs = list(qs[: self.opt.pagesize])
            if len(qs) == 0:
                break
            for o in qs:
                if filter is None or filter(o):
                    yield o
            lastIdentifier = qs[-1].identifier
        yield None
