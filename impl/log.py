#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Logging functions

What gets logged, where it gets logged, and how log records are formatted is all
determined by the configuration file. There are eight record types:

  level  message
  -----  -------
  INFO   transactionId BEGIN function args...
  INFO   transactionId PROGRESS function
  INFO   transactionId END SUCCESS [args...]
  INFO   transactionId END BADREQUEST
  INFO   transactionId END FORBIDDEN
  INFO   - STATUS ...
  ERROR  transactionId END ERROR exception...
  ERROR  - ERROR caller exception...

Records are UTF-8 and percent-encoded so that the following properties hold: log records
contain only graphic ASCII characters and spaces; there is a 1-1 correspondence between
records and lines; and record fields (except for exception strings) are separated by
spaces.
"""

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

import impl.util


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
                _dlm = ""
                for s in reversed(stack[:-1]):
                    fn = s[0]  # .replace(SYS_PATH, "")
                    # fn = fn.replace(ENV_PATH, "")
                    # fn = fn.replace(EZID_PATH, "")
                    ln = str(s[1])
                    op = s[2]
                    pa = s[3]
                    dlm = " " * i + "^-" if i > 0 else ""
                    _LT.debug(f"{dlm}{fn}:{ln}:{op}:{pa}")
                    i += 1
            except Exception as e:
                _LT.exception(e)
        return f(*args, **kwargs)

    return ST


## --

_countLock = threading.Lock()
_errorLock = threading.Lock()

_operationCount = 0
_sentErrors = {}

# def loadConfig():
#     _errorLock.acquire()
#     try:
#     finally:
#         _errorLock.release()
#     _countLock.acquire()
#     try:
#         _operationCount = 0
#     finally:
#         _countLock.release()


def getOperationCount():
    """Return the number of operations (transactions) begun since the last
    reset."""
    return _operationCount


def resetOperationCount():
    """Reset the operation (transaction) counter."""
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
    """Log the start of a transaction."""
    global _operationCount
    # noinspection PyUnresolvedReferences
    _log.info(
        # "%s BEGIN %s" % (transactionId.hex, " ".join(util.encode2(a) for a in args))
        f"{transactionId.hex} BEGIN {' '.join(impl.util.encode2(a) for a in args)}"
    )
    _countLock.acquire()
    try:
        _operationCount += 1
    finally:
        _countLock.release()


def progress(transactionId, function):
    """Log progress made as part of a transaction."""
    _log.info(f"{transactionId.hex} PROGRESS {function}")


def success(transactionId, *args):
    """Log the successful end of a transaction."""
    # noinspection PyUnresolvedReferences
    _log.info(
        # "%s END SUCCESS%s"
        # % (transactionId.hex, "".join(" " + util.encode2(a) for a in args))
        f"{transactionId.hex} END SUCCESS {' '.join(impl.util.encode2(a) for a in args)}"
    )


def badRequest(transactionId):
    """Log the end of a transaction that terminated due to the request being
    faulty."""
    # _log.info("%s END BADREQUEST" % transactionId.hex)
    msg_str = f'{transactionId.hex} END BADREQUEST'
    logging.error(msg_str)
    _log.info(msg_str)


def forbidden(transactionId):
    """Log the end of a transaction that terminated due to an authorization
    failure."""
    _log.info(f"{transactionId.hex} END FORBIDDEN")


def _extractRaiser(tbList):
    # Given a list of traceback frames, returns the qualified name of
    # the EZID function that raised the exception. We try to identify
    # the "best" function to return. Let F be the most recent function
    # in the traceback that is in EZID's code base. We return F unless
    # F is an internal function (begins with an underscore), in which
    # case we return the next most recent function that is public and in
    # the same module as F.
    if tbList is None or len(tbList) == 0:
        return "(unknown)"

    def moduleName(path):
        m = re.match(".*/(.*?)\\.py$", path)
        if m:
            return m.group(1)
        else:
            return "(unknown)"

    j = None
    for i in range(len(tbList) - 1, -1, -1):
        if tbList[i][0].startswith(django.conf.settings.PROJECT_ROOT.as_posix()):
            if tbList[i][2].startswith("_"):
                if j is None or moduleName(tbList[i][0]) == moduleName(tbList[j][0]):
                    j = i
                else:
                    break
            else:
                if j is None or moduleName(tbList[i][0]) == moduleName(tbList[j][0]):
                    j = i
                break
        else:
            if j is not None:
                break
    if j is None:
        j = -1
    return f"{moduleName(tbList[j][0])}.{tbList[j][2]}"


def _notifyAdmins(error):
    t = int(time.time())
    suppress = False
    n = 1
    _errorLock.acquire()
    try:
        # Check if the error is sufficiently similar to a previously-sent
        # error.
        similarError = None
        # noinspection PyUnresolvedReferences
        for e, r in list(_sentErrors.items()):
            # noinspection PyTypeChecker
            if t - r[0] > django.conf.settings.EMAIL_ERROR_LIFETIME:
                # Error has expired; remove it from cache.
                # noinspection PyUnresolvedReferences
                del _sentErrors[e]
            else:
                # noinspection PyTypeChecker
                if e == error or difflib.SequenceMatcher(
                    lambda c: c.isspace(), error, e
                ).ratio() >= float(
                    django.conf.settings.EMAIL_ERROR_SIMILARITY_THRESHOLD
                ):
                    similarError = e
        if similarError is not None:
            # noinspection PyUnresolvedReferences
            r = _sentErrors[similarError]
            # noinspection PyTypeChecker
            if t - r[0] <= django.conf.settings.EMAIL_ERROR_SUPPRESSION_WINDOW:
                r[1] += 1
                suppress = True
            else:
                n += r[1]
                r[0] = t
                r[1] = 0
        else:
            # noinspection PyUnresolvedReferences
            _sentErrors[error] = [t, 0]
    finally:
        _errorLock.release()
    if not suppress:
        if n > 1:
            m = (
                "The following error (or errors similar to it) have occurred "
                "{:d} times since the last notification.".format(n)
            )
        else:
            m = "The following error occurred."
        # noinspection PyTypeChecker
        m += (
            "  Notifications of any additional occurrences of this error "
            "will be suppressed for the next {}.\n\n{}".format(
                str(
                    datetime.timedelta(
                        seconds=django.conf.settings.EMAIL_ERROR_SUPPRESSION_WINDOW
                    )
                ),
                error,
            )
        )
        django.core.mail.mail_admins("EZID error", m, fail_silently=True)


def error(transactionId, exception):
    """Trigger Django's dynamic exception report or send the exception and
    traceback to the Django administrator list.

    Must be called from an exception handler.
    """

    traceback.print_tb(exception.__traceback__)

    if django.conf.settings.DEBUG:
        # Pass the exception up to Django, which renders a dynamic exception report.
        raise exception

    m = str(exception)
    if len(m) > 0:
        m = ": " + m
    _log.error(
        "{} END ERROR {}{}".format(
            transactionId.hex,
            impl.util.encode1(type(exception).__name__),
            impl.util.encode1(m),
        )
    )
    _notifyAdmins(
        "Exception raised in {}:\n{}{}\n\n{}".format(
            _extractRaiser(traceback.extract_tb(sys.exc_info()[2])),
            type(exception).__name__,
            m,
            traceback.format_exc(),
        )
    )


def otherError(caller, exception):
    """Log an internal exception.

    Also, if the Django DEBUG flag is false, mails a traceback to the Django
    administrator list.
    """
    m = str(exception)
    if len(m) > 0:
        m = ": " + m
    _log.error(
        "- ERROR {} {}{}".format(
            impl.util.encode2(caller),
            impl.util.encode1(type(exception).__name__),
            impl.util.encode1(m),
        )
    )
    if django.conf.settings.DEBUG:
        raise exception
    else:
        _notifyAdmins(
            "Exception raised in {}:\n{}{}\n\n{}".format(
                caller, type(exception).__name__, m, traceback.format_exc()
            )
        )


# def status(*args):
#     """Log the server's status."""
#     _log.info("- STATUS " + " ".join(impl.util.encode1(a) for a in args))
