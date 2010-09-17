# =============================================================================
#
# EZID :: log.py
#
# Logging functions.  What gets logged, where it gets logged, and how
# log records are formatted is all determined by the configuration
# file.  There are six record types:
#
#   level  message
#   -----  -------
#   INFO   transactionId BEGIN function args...
#   INFO   transactionId END SUCCESS [args...]
#   INFO   transactionId END BADREQUEST
#   INFO   transactionId END UNAUTHORIZED
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

import django.conf
import django.core.mail
import logging
import logging.config
import traceback

import util

logging.config.fileConfig(django.conf.settings.EZID_CONFIG_FILE,
  { "SITE_ROOT": django.conf.settings.SITE_ROOT })
_log = logging.getLogger()

def begin (transactionId, *args):
  """
  Logs the start of a transaction.
  """
  _log.info("%s BEGIN %s" % (transactionId.hex,
    " ".join(util.encode2(a) for a in args)))

def success (transactionId, *args):
  """
  Logs the successful end of a transaction.
  """
  _log.info("%s END SUCCESS%s" % (transactionId.hex,
    "".join(" " + util.encode2(a) for a in args)))

def badRequest (transactionId):
  """
  Logs the end of a transaction that terminated due to the request
  being faulty.
  """
  _log.info("%s END BADREQUEST" % transactionId.hex)

def unauthorized (transactionId):
  """
  Logs the end of a transaction that terminated due to an
  authorization failure.
  """
  _log.info("%s END UNAUTHORIZED" % transactionId.hex)

def error (transactionId, exception):
  """
  Logs the end of a transaction that terminated due to an internal
  error.  Also, if the Django DEBUG flag is false, mails a traceback
  to the Django administrator list.  Must be called from an exception
  handler.
  """
  m = str(exception)
  if len(m) > 0: m = ": " + m
  _log.error("%s END ERROR %s%s" % (transactionId.hex,
    util.encode1(type(exception).__name__), util.encode1(m)))
  if not django.conf.settings.DEBUG:
    django.core.mail.mail_admins("EZID exception", traceback.format_exc(),
      fail_silently=True)

def otherError (caller, exception):
  """
  Logs an internal error.  Also, if the Django DEBUG flag is false,
  mails a traceback to the Django administrator list.  Must be called
  from an exception handler.
  """
  m = str(exception)
  if len(m) > 0: m = ": " + m
  _log.error("- ERROR %s %s%s" % (util.encode2(caller),
    util.encode1(type(exception).__name__), util.encode1(m)))
  if not django.conf.settings.DEBUG:
    django.core.mail.mail_admins("EZID exception", traceback.format_exc(),
      fail_silently=True)
