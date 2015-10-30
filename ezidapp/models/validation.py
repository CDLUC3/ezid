# =============================================================================
#
# EZID :: ezidapp/models/validation.py
#
# Model validation functions.
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
  if not datacenterSymbolRE.match(symbol) or symbol[-1] == "\n":
    raise django.core.exceptions.ValidationError("Invalid datacenter symbol.")

# EZID borrows its resource type vocabulary from DataCite, and extends
# that vocabulary by allowing a "specific type" (in DataCite parlance)
# to follow a "general type" (or type proper) separated by a slash, as
# in "Image/Photograph".  The following dictionary lists the allowable
# resource types (these are from version 3.1 of the DataCite Metadata
# Schema <http://schema.datacite.org/meta/kernel-3/>) and maps them to
# single-character mnemonic codes for database storage purposes.

resourceTypes = {
  "Audiovisual": "A",
  "Collection": "C",
  "Dataset": "D",
  "Event": "E",
  "Image": "I",
  "InteractiveResource": "N",
  "Model": "M",
  "PhysicalObject": "P",
  "Service": "V",
  "Software": "S",
  "Sound": "U",
  "Text": "T",
  "Workflow": "W",
  "Other": "O"
}

def resourceType (descriptor):
  # Validates a resource type that is possibly extended with a
  # specific type as described above.  Returns a pair
  # (mnemonicCode, normalizedDescriptor).
  descriptor = descriptor.strip()
  if "/" in descriptor:
    gt, st = descriptor.split("/", 1)
    gt = gt.strip()
    st = st.strip()
  else:
    gt = descriptor
    st = ""
  if gt not in resourceTypes:
    raise django.core.exceptions.ValidationError("Invalid resource type.")
  return (resourceTypes[gt], gt+"/"+st if st != "" else gt)

goodCrossrefStatusRE = re.compile("(awaiting status change to public|" +\
  "registration in progress|successfully registered)$")
badCrossrefStatusRE = re.compile("(registered with warning|" +\
  "registration failure) \| [^ ]")

def crossrefStatusOrEmpty (value):
  # Validates that a string is either empty or a CrossRef status.
  value = value.strip()
  if value != "":
    if not goodCrossrefStatusRE.match(value) and\
      not badCrossrefStatusRE.match(value):
      raise django.core.exceptions.ValidationError(
        "Malformed CrossRef status.")
