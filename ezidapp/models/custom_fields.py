# =============================================================================
#
# EZID :: ezidapp/models/custom_fields.py
#
# Custom model fields.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.core.exceptions
import django.db.models
import json
import zlib

import util

class CompressedJsonField (django.db.models.BinaryField):
  # Stores an arbitrary (well, pickle-able) Python object as a gzipped
  # JSON string.

  def get_db_prep_save (self, value, *args, **kwargs):
    if value is None:
      return None
    else:
      try:
        return super(CompressedJsonField, self).get_db_prep_save(
          zlib.compress(json.dumps(value, separators=(",", ":"))), *args,
          **kwargs)
      except Exception, e:
        raise django.core.exceptions.ValidationError(
          "Exception encountered packing compressed JSON database value: " +\
          util.formatException(e))

  def from_db_value (self, value, *args, **kwargs):
    if value is None:
      return None
    else:
      try:
        return json.loads(zlib.decompress(value))
      except Exception, e:
        raise django.core.exceptions.ValidationError(
          "Exception encountered unpacking compressed JSON database value: " +\
          util.formatException(e))
