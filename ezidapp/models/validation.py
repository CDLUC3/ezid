# =============================================================================
#
# EZID :: ezidapp/models/validation.py
#
# Common model validation functions.
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
import re

import util

def nonEmpty (value):
  # Validates that a string has at least one non-whitespace character.
  # (Sadly, Django's blank=False field option checks only that string
  # values are not empty; they can still be entirely whitespace.)
  if value.strip() == "":
    raise django.core.exceptions.ValidationError("This field cannot be blank.")

def anyIdentifier (identifier):
  # Validates that a string corresponds to the qualified, normalized
  # form of any known type of identifier.
  i = util.validateIdentifier(identifier)
  if i is None:
    raise django.core.exceptions.ValidationError("Invalid identifier.")
  if i != identifier:
    raise django.core.exceptions.ValidationError(
      "Identifier is not in normalized form.")

def agentPid (pid):
  # Validates an agent (i.e., user or group) persistent identifier.
  # This function does not check that the identifier actually exists;
  # that's left to the calling code.  In practice agent identifiers
  # will all fall under a particular shoulder, but for validation
  # purposes we require only that they be ARKs.
  if not pid.startswith("ark:/") or util.validateArk(pid[5:]) != pid[5:]:
    raise django.core.exceptions.ValidationError(
      "Invalid agent persistent identifier.")

datacenterSymbolRE = re.compile(
  "^([A-Z][-A-Z0-9]{0,6}[A-Z0-9])\.([A-Z][-A-Z0-9]{0,6}[A-Z0-9])$", re.I)
maxDatacenterSymbolLength = 17

def datacenterSymbol (symbol):
  # Validates a DataCite datacenter symbol, per DataCite rules.
  if not datacenterSymbolRE.match(symbol):
    raise django.core.exceptions.ValidationError("Invalid datacenter symbol.")
