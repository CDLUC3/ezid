# =============================================================================
#
# EZID :: datacite_async.py
#
# Asynchronous DataCite processing.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.conf
import uuid

import config
import datacite
import ezidapp.models
import register_async

_daemonEnabled = [None]
_threadName = [None]

def _uploadMetadata (doi, metadata, datacenter):
  r = datacite.uploadMetadata(doi[4:], {}, metadata, True, datacenter)
  assert type(r) is not str, "unexpected return: " + r

def _setTargetUrl (doi, targetUrl, datacenter):
  r = datacite.setTargetUrl(doi[4:], targetUrl, datacenter)
  assert type(r) is not str, "unexpected return: " + r

def _overwrite (sh, rows, doi, metadata):
  register_async.callWrapper(sh, rows, "datacite.uploadMetadata",
    _uploadMetadata, doi, metadata, metadata["_d"])
  register_async.callWrapper(sh, rows, "datacite.setTargetUrl",
    _setTargetUrl, doi, metadata["_t"], metadata["_d"])
  if metadata.get("_is", "public") != "public" or\
    metadata.get("_x", "yes") != "yes":
    register_async.callWrapper(sh, rows, "datacite.deactivate",
      datacite.deactivate, doi[4:], metadata["_d"])

def _delete (sh, rows, doi, metadata):
  # We can't actually delete a DOI, so we do the next best thing...
  register_async.callWrapper(sh, rows, "datacite.setTargetUrl",
    _setTargetUrl, doi, "http://datacite.org/invalidDOI",
    metadata["_d"])
  register_async.callWrapper(sh, rows, "datacite.deactivate",
    datacite.deactivate, doi[4:], metadata["_d"])

def enqueueIdentifier (identifier, operation, blob):
  """
  Adds an identifier to the DataCite asynchronous processing queue.
  'identifier' should be the normalized, qualified identifier, e.g.,
  "doi:10.5060/FOO".  'operation' is the identifier operation and
  should be one of the strings "create", "update", or "delete".
  'blob' is the identifier's metadata dictionary in blob form.
  """
  register_async.enqueueIdentifier(ezidapp.models.DataciteQueue,
    identifier, operation, blob)

def getQueueLength ():
  """
  Returns the length of the DataCite queue.
  """
  return ezidapp.models.DataciteQueue.objects.count()

def _loadConfig ():
  _daemonEnabled[0] = django.conf.settings.DAEMON_THREADS_ENABLED and\
    config.get("daemons.datacite_enabled").lower() == "true"
  if _daemonEnabled[0]:
    _threadName[0] = uuid.uuid1().hex
    register_async.launch("datacite", ezidapp.models.DataciteQueue,
      _overwrite, _overwrite, _delete, None, None, None,
      int(config.get("daemons.datacite_num_worker_threads")),
      int(config.get("daemons.datacite_processing_idle_sleep")),
      int(config.get("daemons.datacite_processing_error_sleep")),
      _daemonEnabled, _threadName)

_loadConfig()
config.registerReloadListener(_loadConfig)
