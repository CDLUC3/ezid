# =============================================================================
#
# EZID :: log.py
#
# Logging functions.  What gets logged, where it gets logged, and how
# log records are formatted is all determined by the configuration
# file.  There are eight record types:
#
#   level  message
#   -----  -------
#   INFO   transactionId BEGIN function args...
#   INFO   transactionId PROGRESS function
#   INFO   transactionId END SUCCESS [args...]
#   INFO   transactionId END BADREQUEST
#   INFO   transactionId END FORBIDDEN
#   INFO   - STATUS ...
#   ERROR  transactionId END ERROR exception...
#   ERROR  - ERROR caller exception...
#
# Records are UTF-8 and percent-encoded so that the following
# properties hold: log records contain only graphic ASCII characters
# and spaces; there is a 1-1 correspondence between records and lines;
# and record fields (except for exception strings) are separated by
# spaces.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2010, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import datetime
import difflib
import logging
import logging.config
import os.path
import re
import sys
import threading
import time
import traceback

import django.conf
import django.core.mail

import config
import util


## DV ++
## for performance reasons, this code should not be enabled in a production environment
## @stacklog decorator for assisting with call tracing

# TODO: If we need these to work in CI, will need to move to using the inspect module.
# SYS_PATH = os.path.abspath(os.path.join(os.path.dirname(threading.__file__), ".."))
# ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(datetime.__file__), ".."))
# EZID_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def stacklog(f):
    def ST(*args, **kwargs):
        _LT = logging.getLogger("tracer")
        if _LT.level >= logging.DEBUG:
            try:
                stack = traceback.extract_stack()
                i = 0
                dlm = ""
                for s in reversed(stack[:-1]):
                    fn = s[0] #.replace(SYS_PATH, "")
                    # fn = fn.replace(ENV_PATH, "")
                    # fn = fn.replace(EZID_PATH, "")
                    ln = str(s[1])
                    op = s[2]
                    pa = s[3]
                    dlm = " " * i + "^-" if i > 0 else ""
                    _LT.debug("%s%s:%s:%s:%s" % (dlm, fn, ln, op, pa))
                    i += 1
            except Exception as e:
                _LT.exception(e)
        return f(*args, **kwargs)

    return ST


## --

_errorLock = threading.Lock()
_countLock = threading.Lock()
_operationCount = 0
_suppressionWindow = None
_errorLifetime = None
_errorSimilarityThreshold = None
_sentErrors = None


def loadConfig():
    global _operationCount, _suppressionWindow, _errorLifetime
    global _errorSimilarityThreshold, _sentErrors
    _errorLock.acquire()
    try:
        _suppressionWindow = int(config.get("email.error_suppression_window"))
        _errorLifetime = int(config.get("email.error_lifetime"))
        _errorSimilarityThreshold = float(
            config.get("email.error_similarity_threshold")
        )
        _sentErrors = {}
    finally:
        _errorLock.release()
    _countLock.acquire()
    try:
        _operationCount = 0
    finally:
        _countLock.release()


def getOperationCount():
    """
  Returns the number of operations (transactions) begun since the last
  reset.
  """
    return _operationCount


def resetOperationCount():
    """
  Resets the operation (transaction) counter.
  """
    global _operationCount
    _countLock.acquire()
    try:
        _operationCount = 0
    finally:
        _countLock.release()


# In the following, it is important that we only augment the existing
# logging, not overwrite it, for Django also uses Python's logging
# facility.
if django.conf.settings.LOGGING_CONFIG_FILE:
    logging.config.fileConfig(
        os.path.join(
            django.conf.settings.SETTINGS_DIR, django.conf.settings.LOGGING_CONFIG_FILE
        ),
        {"SITE_ROOT": django.conf.settings.SITE_ROOT},
        disable_existing_loggers=False,
    )

_log = logging.getLogger()


def begin(transactionId, *args):
    """
  Logs the start of a transaction.
  """
    global _operationCount
    _log.info(
        "%s BEGIN %s" % (transactionId.hex, " ".join(util.encode2(a) for a in args))
    )
    _countLock.acquire()
    try:
        _operationCount += 1
    finally:
        _countLock.release()


def progress(transactionId, function):
    """
  Logs progress made as part of a transaction.
  """
    _log.info("%s PROGRESS %s" % (transactionId.hex, function))


def success(transactionId, *args):
    """
  Logs the successful end of a transaction.
  """
    _log.info(
        "%s END SUCCESS%s"
        % (transactionId.hex, "".join(" " + util.encode2(a) for a in args))
    )


def badRequest(transactionId):
    """
  Logs the end of a transaction that terminated due to the request
  being faulty.
  """
    _log.info("%s END BADREQUEST" % transactionId.hex)


def forbidden(transactionId):
    """
  Logs the end of a transaction that terminated due to an
  authorization failure.
  """
    _log.info("%s END FORBIDDEN" % transactionId.hex)


def _extractRaiser(tbList):
    # Given a list of traceback frames, returns the qualified name of
    # the EZID function that raised the exception.  We try to identify
    # the "best" function to return.  Let F be the most recent function
    # in the traceback that is in EZID's code base.  We return F unless
    # F is an internal function (begins with an underscore), in which
    # case we return the next most recent function that is public and in
    # the same module as F.
    if tbList == None or len(tbList) == 0:
        return "(unknown)"

    def moduleName(path):
        m = re.match(".*/(.*?)\.py$", path)
        if m:
            return m.group(1)
        else:
            return "(unknown)"

    j = None
    for i in range(len(tbList) - 1, -1, -1):
        if tbList[i][0].startswith(django.conf.settings.PROJECT_ROOT):
            if tbList[i][2].startswith("_"):
                if j == None or moduleName(tbList[i][0]) == moduleName(tbList[j][0]):
                    j = i
                else:
                    break
            else:
                if j == None or moduleName(tbList[i][0]) == moduleName(tbList[j][0]):
                    j = i
                break
        else:
            if j != None:
                break
    if j == None:
        j = -1
    return "%s.%s" % (moduleName(tbList[j][0]), tbList[j][2])


def _notifyAdmins(error):
    t = int(time.time())
    suppress = False
    n = 1
    _errorLock.acquire()
    try:
        # Check if the error is sufficiently similar to a previously-sent
        # error.
        similarError = None
        for e, r in _sentErrors.items():
            if t - r[0] > _errorLifetime:
                # Error has expired; remove it from cache.
                del _sentErrors[e]
            else:
                if (
                    e == error
                    or difflib.SequenceMatcher(lambda c: c.isspace(), error, e).ratio()
                    >= _errorSimilarityThreshold
                ):
                    similarError = e
        if similarError != None:
            r = _sentErrors[similarError]
            if t - r[0] <= _suppressionWindow:
                r[1] += 1
                suppress = True
            else:
                n += r[1]
                r[0] = t
                r[1] = 0
        else:
            _sentErrors[error] = [t, 0]
    finally:
        _errorLock.release()
    if not suppress:
        if n > 1:
            m = (
                "The following error (or errors similar to it) have occurred "
                + "%d times since the last notification."
            ) % n
        else:
            m = "The following error occurred."
        m += (
            "  Notifications of any additional occurrences of this error "
            + "will be suppressed for the next %s.\n\n%s"
        ) % (str(datetime.timedelta(seconds=_suppressionWindow)), error)
        django.core.mail.mail_admins("EZID error", m, fail_silently=True)


def error(transactionId, exception):
    """Trigger Django's dynamic exception report or send the exception and traceback to
  the Django administrator list. Must be called from an exception handler.
  """
    if django.conf.settings.DEBUG:
        # Pass the exception up to Django, which renders a dynamic exception report.
        raise exception

    m = str(exception)
    if len(m) > 0:
        m = ": " + m
    _log.error(
        "%s END ERROR %s%s"
        % (transactionId.hex, util.encode1(type(exception).__name__), util.encode1(m))
    )
    _notifyAdmins(
        "Exception raised in %s:\n%s%s\n\n%s"
        % (
            _extractRaiser(traceback.extract_tb(sys.exc_info()[2])),
            type(exception).__name__,
            m,
            traceback.format_exc(),
        )
    )


def otherError(caller, exception):
    """
  Logs an internal error.  Also, if the Django DEBUG flag is false,
  mails a traceback to the Django administrator list.  Must be called
  from an exception handler.
  """
    m = str(exception)
    if len(m) > 0:
        m = ": " + m
    _log.error(
        "- ERROR %s %s%s"
        % (
            util.encode2(caller),
            util.encode1(type(exception).__name__),
            util.encode1(m),
        )
    )
    if not django.conf.settings.DEBUG:
        _notifyAdmins(
            "Exception raised in %s:\n%s%s\n\n%s"
            % (caller, type(exception).__name__, m, traceback.format_exc())
        )


def status(*args):
    """
  Logs the server's status.
  """
    _log.info("- STATUS " + " ".join(util.encode1(a) for a in args))
