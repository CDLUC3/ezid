#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Check target links

Link checker that tests EZID target URLs. Only non-default target URLs of public, real
identifiers are tested.

This script runs continuously and indefinitely. It runs independently of the main EZID
server, and may even run on a different machine, but is nevertheless loosely coupled to
EZID in two ways:

    1) It communicates with EZID through EZID's search database. Specifically, the link
    checker maintains its own table of identifiers and target URLs which it periodically
    updates from the main EZID tables, and conversely, the EZID server periodically
    uploads link checker results back into its tables. These update mechanisms are
    asynchronous from mainline EZID processing.

    2) The link checker lives in and uses some of EZID's codebase, principally to enable
    database access.

The link checker tests a target URL by performing a GET request on the URL. A timely
200 response equates to success.

Between periodic (say, weekly) table updates the link checker processes limited-size
worksets. A workset consists of the "oldest" target URLs (those that were last checked
longest ago) from each owner, up to a maximum number per owner. Parallel Worker threads
then visit the URLs in round-robin fashion (i.e., visit one URL from each owner, then
repeat the cycle) so as to dilute the burden the link checker places on external
servers. Additionally, the link checker imposes a minimum interval between successive
checks against the same owner. (There is typically a high correlation between owners
and servers.)

Blackout windows are an important feature. Target URLs are not re-checked within a
certain window of time (say, one month). Combined with the round-robin processing
described above, the intention is to balance timeliness and exhaustivity (all target
URLs will eventually be checked) and fairness (the checks of any given owner's target
URLs will not be excessively delayed because another owner has many more identifiers
than it). Additionally, previously failed target URLs utilize a different window (say,
1-2 days) and are given priority in populating worksets, to allow failures to be
re-checked more frequently.

Failures are not reported immediately because transient outages are frequently
encountered. Only after a target URL consecutively fails some number of checks (say, a
dozen over a span of two weeks) is it considered notification-worthy.

Target URLs can be excluded from checking on a per-owner basis. An exclusion file can
be specified on the command line; the file should contain lines of the form:

    username {permanent|temporary}

For example:

    # this is a comment line
    merritt temporary
    data-planet permanent

Permanent exclusion differs from temporary in that if an owner is permanently excluded,
its identifiers and target URLs are not entered into the link checker's table at all.

The link checker notices within a few seconds when the exclusion file has been modified.
Examine the link checker's log file to confirm that it has been reloaded successfully.

There is also the option to exclude identifiers based on a regular expression which will
usually be used to exclude shoulders, but can be more flexible if needed. These
variables in the settings file control this behavior:

    LINKCHECKER_ID_EXCLUSION_ENABLED = True
    LINKCHECKER_ID_EXCLUSION_FILE = 'path/to/id_exclusion_file.txt'

The id exclusion file should contain regular expression patterns, one per line, that
match identifiers to be excluded. Lines starting with '#' or empty lines are ignored.

The regular expressions are case-insensitive and would typically be things such as
`^ark:/13030/c8` which anchor at the beginning of the identifier for shoulder matching.

The regular expressions are combined into a single regex pattern that is used for matching any (|).
This approach should work for a moderate number of patterns (say less than 1,000) and if we have large
numbers of patterns, we may need to consider a different approach because performance may degrade.
I suspect that only a limited number of patterns (shoulders) will be needed for exclusion in practice
so we will likely not need to worry about performance issues from having too many patterns.
"""

# noinspection PyUnresolvedReferences

import http.client
import http.cookiejar
import logging
import os
import re
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import time

import django.apps
import django.conf
import django.core.management

import ezidapp.management.commands.proc_base
import ezidapp.models.async_queue
import ezidapp.models.identifier

# import ezidapp.models.link_checker
import ezidapp.models.user
import impl
import impl.util
import traceback

def simple_error(e):
    """Extracts the exception name, HTTP status code (if applicable), filename, and line number."""
    tb = traceback.extract_tb(e.__traceback__)[0]  # Get last traceback entry
    error_msg = f"{type(e).__name__} in {tb.filename} at line {tb.lineno}"

    # If it's an HTTPError, include the status code
    if isinstance(e, urllib.error.HTTPError):
        error_msg += f" (HTTP {e.code})"

    return error_msg


log = logging.getLogger(__name__)
_lock = threading.Lock()


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    name = __name__
    setting = 'DAEMONS_LINKCHECKER_ENABLED'

    def __init__(self):
        super().__init__()
        self._exclusionFileModifyTime = -1
        self._lastExclusionFileCheckTime = -1
        self._permanentExcludes = []
        self._temporaryExcludes = []
        self._exclusionFile = None

        self._idExclusionFileModifyTime = -1
        self._idLastExclusionFileCheckTime = -1
        self._idExclusionFile = None
        self._idExclusionRegex = None

    def run(self):
        if django.conf.settings.LINKCHECKER_EXCLUSION_ENABLED:
            if django.conf.settings.LINKCHECKER_EXCLUSION_FILE is not None:
                self._exclusionFile = django.conf.settings.LINKCHECKER_EXCLUSION_FILE
                log.info(f"Link checker exclusion enabled with file: {self._exclusionFile}")

        if django.conf.settings.LINKCHECKER_ID_EXCLUSION_ENABLED:
            if django.conf.settings.LINKCHECKER_ID_EXCLUSION_FILE is not None:
                self._idExclusionFile = django.conf.settings.LINKCHECKER_ID_EXCLUSION_FILE
                log.info(f"Link checker ID exclusion enabled with file: {self._idExclusionFile}")

        while not self.terminated():
            self.check_all()

    def now(self):
        return time.time()

    def check_all(self):
        start = self.now()
        self.updateDatabaseTable()
        # The following flag is used to ensure at least one round gets
        # fully processed. In general rounds may be interrupted.
        firstRound = True
        while (
            firstRound
            or self.remaining(start, django.conf.settings.LINKCHECKER_TABLE_UPDATE_CYCLE) > 0
        ):
            if self.terminated():
                break
            self.loadWorkset()
            log.info("begin processing")
            # noinspection PyTypeChecker
            if len(self._workset) > 0:
                roundStart = self.now()
                self._stopNow = False
                self._index = 0
                self._totalSleepTime = 0
                if firstRound:
                    timeout = None
                else:
                    # The first component in the computation of the timeout
                    # below causes table updates to occur at regular, specific
                    # times (admittedly, there's no real reason for that goal,
                    # but that's its purpose anyway). The second component
                    # addresses the situation that some owners may push every
                    # check to the timeout limit, which causes the link checker
                    # to be idle for all other owners for long periods of time.
                    # By shortening the timeout we force worksets to be loaded
                    # more frequently. We allot enough time for a nominal
                    # workset to be processed, i.e., an owner's maximum number
                    # of links, each of which is assumed to be checkable in
                    # 1 second.
                    timeout = min(
                        self.remaining(start, django.conf.settings.LINKCHECKER_TABLE_UPDATE_CYCLE),
                        django.conf.settings.LINKCHECKER_WORKSET_OWNER_MAX_LINKS
                        * (1 + django.conf.settings.LINKCHECKER_OWNER_REVISIT_MIN_INTERVAL),
                    )
                threads = []
                for i in range(django.conf.settings.LINKCHECKER_NUM_WORKERS):
                    t = threading.Thread(target=self.worker)
                    t.start()
                    threads.append(t)
                for i in range(django.conf.settings.LINKCHECKER_NUM_WORKERS):
                    threads[i].join(timeout)
                    if threads[i].is_alive():
                        # If the thread is still alive it must have timed out,
                        # meaning it's time to terminate it and all remaining
                        # threads.
                        self._stopNow = True
                        timeout = None
                        threads[i].join()
                # noinspection PyTypeChecker
                numChecked = sum(ow.nextIndex for ow in self._workset)
                rate = numChecked / (self.now() - roundStart)
                try:
                    if rate >= 1 / 1.05:  # using this bound avoids printing 1/1.0
                        rate = str(round(rate, 1)) + " links/s"
                    else:
                        rate = "1/%s link/s" % str(round(1 / rate, 1))
                    log.info(
                        f"end processing, checked {numChecked} links at {rate}, slept {self.toHms(self._totalSleepTime)}"
                    )
                except ZeroDivisionError:
                    log.info(
                        f"end processing, checked {numChecked}, slept {self.toHms(self._totalSleepTime)}"
                    )
            else:
                # The sleep below is just to prevent a compute-intensive loop.
                log.info("end processing (nothing to check)")
                self.sleep(60)
            firstRound = False

    @staticmethod
    def s(n):
        if n != 1:
            return "s"
        else:
            return ""

    @staticmethod
    def toHms(seconds):
        h = seconds / 3600
        seconds -= h * 3600
        m = seconds / 60
        s = seconds - m * 60
        return "%02d:%02d:%02d" % (h, m, s)

    def remaining(self, start, cycle):
        return max(cycle - (self.now() - start), 0.0)

    def daysSince(self, when):
        return int((self.now() - when) / 86400)

    def loadIdExclusionFile(self):
        if self._idExclusionFile is None:
            return
        if self.now_int() - self._idLastExclusionFileCheckTime < 10:
            return
        self._idLastExclusionFileCheckTime = self.now_int()
        f = None
        s = None
        try:
            # noinspection PyTypeChecker
            s = os.stat(self._idExclusionFile)
            if s.st_mtime == self._idExclusionFileModifyTime:
                return
            # noinspection PyTypeChecker
            f = open(self._idExclusionFile)

            id_exclusion = []
            n = 0
            for l in f:
                n += 1
                if l.strip() == "" or l.startswith("#"):
                    continue
                try:
                    re.compile(l.strip(), re.IGNORECASE)
                    # To let each sub-pattern anchor separately, you can embed the anchors inside the
                    # non-capturing group (the (?: ... ) part)
                    id_exclusion.append(f"(?:{l.strip()})")
                except re.error:
                    log.error('Regular expression error in id exclusion file')
                    assert False, "regular expression error on line %d" % n

            combined = "|".join(id_exclusion)
            self._idExclusionRegex = re.compile(combined, re.IGNORECASE)
            self._exclusionFileModifyTime = s.st_mtime
            log.info("id exclusion file successfully loaded")
        except Exception as e:
            log.error('Exception')
            if s is not None:
                self._exclusionFileModifyTime = s.st_mtime
            log.error("error loading exclusion file: " + str(e))
        finally:
            if f is not None:
                f.close()


    def loadExclusionFile(self):
        if self._exclusionFile is None:
            return
        if self.now_int() - self._lastExclusionFileCheckTime < 10:
            return
        self._lastExclusionFileCheckTime = self.now_int()
        f = None
        s = None
        try:
            # noinspection PyTypeChecker
            s = os.stat(self._exclusionFile)
            if s.st_mtime == self._exclusionFileModifyTime:
                return
            # noinspection PyTypeChecker
            f = open(self._exclusionFile)
            pe = []
            te = []
            n = 0
            for l in f:
                n += 1
                if l.strip() == "" or l.startswith("#"):
                    continue
                try:
                    user, flag = l.split()
                except ValueError:
                    log.error('ValueError')
                    assert False, "syntax error on line %d" % n
                assert flag in ["permanent", "temporary"], "syntax error on line %d" % n

                # search_user_model = django.apps.apps.get_model('ezidapp', 'User')

                try:
                    (pe if flag == "permanent" else te).append(
                        ezidapp.models.user.User.objects.get(username=user).id
                    )
                except ezidapp.models.user.User.DoesNotExist:
                    log.error('User.DoesNotExist')
                    assert False, "no such user: " + user
            self._permanentExcludes = pe
            self._temporaryExcludes = te
            self._exclusionFileModifyTime = s.st_mtime
            log.info("exclusion file successfully loaded")
        except Exception as e:
            log.error('Exception')
            if s is not None:
                self._exclusionFileModifyTime = s.st_mtime
            log.error("error loading exclusion file: " + str(e))
        finally:
            if f is not None:
                f.close()

    def harvest(self, model, only=None, filter=None):
        lastIdentifier = ""
        while not self.terminated():
            qs = model.objects.filter(identifier__gt=lastIdentifier).order_by("identifier")
            if only is not None:
                qs = qs.only(*only)
            qs = list(qs[:1000])
            if len(qs) == 0:
                break
            for o in qs:
                # added to exclude ID patterns if they match the id exclusion regex in addition to normal filtering
                if (filter is None or filter(o)) and \
                     (self._idExclusionRegex is None or not self._idExclusionRegex.search(o.identifier)):
                    # log.debug(f'Generator returning: {str(o)}')
                    yield o
            lastIdentifier = qs[-1].identifier
        yield None

    def updateDatabaseTable(self):
        self.loadExclusionFile()
        self.loadIdExclusionFile()
        log.info("begin update table")
        numIdentifiers = 0
        numAdditions = 0
        numDeletions = 0
        numUpdates = 0
        numUnvisited = 0
        good = [0, 0, self.now_int()]  # [total, to visit, oldest timestamp]
        bad = [0, 0, self.now_int()]

        link_checker_model = django.apps.apps.get_model('ezidapp', 'LinkChecker')
        lcGenerator = self.harvest(link_checker_model)

        search_identifier_model = django.apps.apps.get_model('ezidapp', 'SearchIdentifier')
        siGenerator = self.harvest(
            search_identifier_model,
            ["identifier", "owner", "status", "target", "isTest"],
            lambda si: si.isPublic
            and not si.isTest
            and si.target != si.defaultTarget
            and si.owner_id not in self._permanentExcludes,
        )

        lc = next(lcGenerator)
        si = next(siGenerator)
        while lc is not None or si is not None:
            if lc is not None and (si is None or lc.identifier < si.identifier):
                numDeletions += 1
                lc.delete()
                lc = next(lcGenerator)
            elif si is not None and (lc is None or si.identifier < lc.identifier):
                numIdentifiers += 1
                numAdditions += 1
                numUnvisited += 1
                nlc = link_checker_model(
                    identifier=si.identifier,
                    target=si.target,
                    owner_id=si.owner_id,
                )
                nlc.full_clean(validate_unique=False)
                nlc.save()
                si = next(siGenerator)
            else:
                numIdentifiers += 1
                # noinspection PyUnresolvedReferences,PyUnresolvedReferences
                if lc.owner_id != si.owner_id or lc.target != si.target:
                    numUpdates += 1
                    numUnvisited += 1
                    lc.owner_id = si.owner_id
                    lc.target = si.target
                    # noinspection PyUnresolvedReferences
                    lc.clearHistory()
                    # noinspection PyUnresolvedReferences
                    lc.full_clean(validate_unique=False)
                    # noinspection PyUnresolvedReferences
                    lc.save()
                else:
                    # noinspection PyUnresolvedReferences
                    if lc.isUnvisited:
                        numUnvisited += 1
                    else:
                        # noinspection PyUnresolvedReferences
                        if lc.isGood:
                            good[0] += 1
                            # noinspection PyUnresolvedReferences
                            if (
                                lc.lastCheckTime
                                < self.now_int()
                                - django.conf.settings.LINKCHECKER_GOOD_RECHECK_MIN_INTERVAL
                            ):
                                good[1] += 1
                            # noinspection PyUnresolvedReferences
                            good[2] = min(good[2], lc.lastCheckTime)
                        else:
                            bad[0] += 1
                            # noinspection PyUnresolvedReferences
                            if (
                                lc.lastCheckTime
                                < self.now_int()
                                - django.conf.settings.LINKCHECKER_BAD_RECHECK_MIN_INTERVAL
                            ):
                                bad[1] += 1
                            # noinspection PyUnresolvedReferences
                            bad[2] = min(bad[2], lc.lastCheckTime)
                lc = next(lcGenerator)
                si = next(siGenerator)
        log.info(
            (
                "end update table, %d identifier%s, %d addition%s, "
                + "%d deletion%s, %d update%s, %d unvisited link%s, "
                + "%d good link%s (%d to check, oldest=%dd), "
                + "%d bad link%s (%d to check, oldest=%dd)"
            )
            % (
                numIdentifiers,
                self.s(numIdentifiers),
                numAdditions,
                self.s(numAdditions),
                numDeletions,
                self.s(numDeletions),
                numUpdates,
                self.s(numUpdates),
                numUnvisited,
                self.s(numUnvisited),
                good[0],
                self.s(good[0]),
                good[1],
                self.daysSince(good[2]),
                bad[0],
                self.s(bad[0]),
                bad[1],
                self.daysSince(bad[2]),
            )
        )

    def loadWorkset(self):
        self._workset = None
        self.loadExclusionFile()
        self.loadIdExclusionFile()
        log.info("begin load workset")
        _workset = []
        numOwnersCapped = 0
        numUnvisited = 0
        good = [0, self.now_int()]  # [total, oldest timestamp]
        bad = [0, self.now_int()]

        search_user_model = django.apps.apps.get_model('ezidapp', 'User')

        for user in search_user_model.objects.all().only("id"):
            if user.id in self._permanentExcludes or user.id in self._temporaryExcludes:
                continue

            def query(isBad, timeBound, limit):
                link_checker_model = django.apps.apps.get_model('ezidapp', 'LinkChecker')
                return list(
                    ezidapp.models.link_checker.LinkChecker.objects.filter(owner_id=user.id)
                    .filter(isBad=isBad)
                    .filter(lastCheckTime__lt=timeBound)
                    .order_by("lastCheckTime")[:limit]
                )

            qs = query(
                True,
                self.now_int() - django.conf.settings.LINKCHECKER_BAD_RECHECK_MIN_INTERVAL,
                django.conf.settings.LINKCHECKER_WORKSET_OWNER_MAX_LINKS,
            )
            if len(qs) > 0:
                bad[0] += len(qs)
                bad[1] = min(bad[1], qs[0].lastCheckTime)
            if django.conf.settings.LINKCHECKER_WORKSET_OWNER_MAX_LINKS - len(qs) > 0:
                q = query(
                    False,
                    self.now_int() - django.conf.settings.LINKCHECKER_GOOD_RECHECK_MIN_INTERVAL,
                    django.conf.settings.LINKCHECKER_WORKSET_OWNER_MAX_LINKS - len(qs),
                )
                if len(q) > 0:
                    qs.extend(q)
                    qgood = [lc for lc in q if lc.isVisited]
                    numUnvisited += len(q) - len(qgood)
                    if len(qgood) > 0:
                        good[0] += len(qgood)
                        good[1] = min(good[1], qgood[0].lastCheckTime)
            if len(qs) > 0:
                _workset.append(OwnerWorkset(user.id, qs))
                if len(qs) == django.conf.settings.LINKCHECKER_WORKSET_OWNER_MAX_LINKS:
                    numOwnersCapped += 1
        numOwners = len(_workset)
        numLinks = numUnvisited + good[0] + bad[0]
        log.info(
            (
                "end load workset, %d owner%s (%d capped), %d link%s, "
                + "%d unvisited link%s, %d good link%s (oldest=%dd), "
                + "%d bad link%s (oldest=%dd)"
            )
            % (
                numOwners,
                self.s(numOwners),
                numOwnersCapped,
                numLinks,
                self.s(numLinks),
                numUnvisited,
                self.s(numUnvisited),
                good[0],
                self.s(good[0]),
                self.daysSince(good[1]),
                bad[0],
                self.s(bad[0]),
                self.daysSince(bad[1]),
            )
        )
        self._workset = _workset

    def getNextLink(self):
        _lock.acquire()
        try:
            self.loadExclusionFile()
            self.loadIdExclusionFile()
            startingIndex = self._index
            allFinished = True
            t = self.now()
            while not self.terminated():
                # noinspection PyUnresolvedReferences
                ow = self._workset[self._index]
                if not ow.isFinished():
                    if (
                        not ow.isLocked
                        and ow.lastCheckTime
                        < t - django.conf.settings.LINKCHECKER_OWNER_REVISIT_MIN_INTERVAL
                    ):
                        ow.isLocked = True
                        return self._index, ow.list[ow.nextIndex]
                    else:
                        allFinished = False
                # noinspection PyTypeChecker
                self._index = (self._index + 1) % len(self._workset)
                if self._index == startingIndex:
                    return "finished" if allFinished else "wait"
        finally:
            _lock.release()

    # noinspection PyUnresolvedReferences
    def markLinkChecked(self, index):
        _lock.acquire()
        try:
            ow = self._workset[index]
            ow.nextIndex += 1
            ow.lastCheckTime = self.now()
            ow.isLocked = False
        finally:
            _lock.release()

    # We're a little conflicted as to how to deal with 401 (unauthorized)
    # and 403 (forbidden) errors. On the one hand, an error was returned
    # instead of the identified object, so the check was a failure; on the
    # other, *something* was at the URL, and presumably with appropriate
    # credentials the identified object would have been returned. Since
    # this script is doing simple link checking, and not landing page
    # analysis, we don't have a way of verifying that an option to
    # authenticate is being provided. So for now we consider 401 and 403
    # errors to be successes.

    def worker(self):
        try:
            while not self.terminated() and not self._stopNow:
                r = self.getNextLink()
                if type(r) is str:
                    if r == "finished":
                        return
                    else:  # wait
                        self.sleep(1)
                        _lock.acquire()
                        try:
                            self._totalSleepTime += 1
                        finally:
                            _lock.release()
                        continue
                index, lc = r
                # Some websites fall into infinite redirect loops if cookies
                # are not utilized.
                o = urllib.request.build_opener(
                    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
                    MyHTTPErrorProcessor(),
                )
                c = None
                mimeType = "unknown"
                try:
                    # This should probably be considered a Python bug, but urllib2
                    # fails if the URL contains Unicode characters. Encoding the
                    # URL as UTF-8 is sufficient.
                    # Another gotcha: some websites require an Accept header.
                    r = urllib.request.Request(
                        lc.target,
                        headers={
                            "User-Agent": django.conf.settings.LINKCHECKER_USER_AGENT,
                            "Accept": "*/*",
                        },
                    )
                    c = o.open(r, timeout=django.conf.settings.LINKCHECKER_CHECK_TIMEOUT)
                    mimeType = c.info().get("Content-Type", "unknown")
                    content = c.read(django.conf.settings.LINKCHECKER_MAX_READ)
                except http.client.IncompleteRead as e:
                    log.error('http.client.IncompleteRead')
                    # Some servers deliver a complete HTML document, but,
                    # apparently expecting further requests from a web browser
                    # that never arrive, hold the connection open and ultimately
                    # deliver a read failure. We consider these cases successes.
                    # noinspection PyUnresolvedReferences
                    if mimeType.startswith("text/html") and re.search(
                        "</\s*html\s*>\s*$", e.partial, re.I
                    ):
                        success = True
                        # noinspection PyUnresolvedReferences
                        content = e.partial
                    else:
                        success = False
                        returnCode = -1
                        lc.checkFailed(returnCode, impl.util.formatException(e))
                except urllib.error.HTTPError as e:
                    log.error(simple_error(e))
                    success = False
                    returnCode = e.code
                except Exception as e:
                    log.error(simple_error(e))
                    success = False
                    returnCode = -1
                    lc.checkFailed(returnCode, impl.util.formatException(e))
                else:
                    success = True
                finally:
                    if c:
                        c.close()

                if success:
                    # noinspection PyUnboundLocalVariable
                    lc.checkSucceeded(mimeType, content)
                else:
                    # noinspection PyUnboundLocalVariable
                    if returnCode >= 0:
                        lc.checkFailed(returnCode)
                lc.full_clean(validate_unique=False)
                lc.save()

                self.markLinkChecked(index)

        except Exception as e:
            log.error(f"Exception: \n{simple_error(e)}")


class OwnerWorkset(Command):
    # Stores primarily a list of links to check that belong to a single
    # owner. 'nextIndex' points to the next unchecked link in the list;
    # if equal to the list length, all links have been checked. While a
    # link is being checked, 'isLocked' is set to True. 'lastCheckTime'
    # is the last time a link from this owner was checked.
    def __init__(self, owner_id, workList):
        super().__init__()
        self.owner_id = owner_id
        self.list = workList  # [LinkChecker, ...]
        self.nextIndex = 0
        self.isLocked = False
        self.lastCheckTime = 0.0

    def isFinished(self):
        # An excluded owner is detected when the link checker's table is
        # updated (in the case of permanent exclusions) and when a workset
        # is loaded (in the case of temporary exclusions). But so that
        # exclusions take more immediate effect when added, we add the
        # check below.
        if not self.isLocked and (
            self.owner_id in self._permanentExcludes or self.owner_id in self._temporaryExcludes
        ):
            self.nextIndex = len(self.list)
        return self.nextIndex >= len(self.list)


class MyHTTPErrorProcessor(urllib.request.HTTPErrorProcessor):
    def http_response(self, request, response):
        if response.status in [401, 403]:
            return response
        else:
            return urllib.request.HTTPErrorProcessor.http_response(self, request, response)

    https_response = http_response
