# =============================================================================
#
# EZID :: mapping.py
#
# Metadata mapping.  This module effectively defines a citation
# metadata standard, which we refer to as "kernel" metadata.
#
# Subtle point: the mappings in this module are not the same as the
# mappings used to satisfy DataCite requirements.  The latter are more
# opportunistic.  For example, to satisfy DataCite, EZID will look to
# the individual DataCite profile elements (datacite.title, etc.) if
# necessary regardless of the declared profile.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2012, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import re

import datacite
import erc
import ezidapp.models.validation
import util

class KernelMetadata (object):
  # Holds kernel citation metadata in attributes 'creator', 'title',
  # 'publisher', 'date', and 'type'.  Each attribute either has a
  # nonempty value or is None.

  def __init__ (self, creator=None, title=None, publisher=None, date=None,
    type=None, validatedType=None):
    self.creator = creator
    self.title = title
    self.publisher = publisher
    self.date = date
    self.type = type
    self._validatedType = validatedType

  @property
  def validatedDate (self):
    if self.date != None:
      try:
        return ezidapp.models.validation.publicationDate(self.date)
      except:
        return None
    else:
      return None

  @property
  def validatedType (self):
    if self._validatedType != None:
      return self._validatedType
    elif self.type != None:
      try:
        return ezidapp.models.validation.resourceType(self.type)
      except:
        return None
    else:
      return None

def _get (d, *keys):
  for k in keys:
    if k in d:
      v = d[k].strip()
      if v != "": return v
  return None

def _mapErcItemized (metadata):
  return KernelMetadata(
    creator=_get(metadata, "erc.who"),
    title=_get(metadata, "erc.what"),
    date=_get(metadata, "erc.when"))

def _mapErc (metadata):
  if _get(metadata, "erc"):
    try:
      d = erc.parse(metadata["erc"])
      return KernelMetadata(
        creator=_get(d, "who"),
        title=_get(d, "what"),
        date=_get(d, "when"))
    except:
      return _mapErcItemized(metadata)
  else:
    return _mapErcItemized(metadata)

# The following dictionary maps lowercased DCMI Type Vocabulary
# <http://dublincore.org/documents/dcmi-type-vocabulary/#H7> terms to
# EZID resource types.

_dublinCoreTypes = {
  "collection": "Collection",
  "dataset": "Dataset",
  "event": "Event",
  "image": "Image",
  "interactiveresource": "InteractiveResource",
  "movingimage": "Audiovisual",
  "physicalobject": "PhysicalObject",
  "service": "Service",
  "software": "Software",
  "sound": "Sound",
  "stillimage": "Image",
  "text": "Text"
}

def _mapDublinCore (metadata):
  type = _get(metadata, "dc.type")
  if type and type.lower() in _dublinCoreTypes:
    vtype = _dublinCoreTypes[type.lower()]
  else:
    vtype = None
  return KernelMetadata(
    creator=_get(metadata, "dc.creator"),
    title=_get(metadata, "dc.title"),
    publisher=_get(metadata, "dc.publisher"),
    date=_get(metadata, "dc.date"),
    type=type,
    validatedType=vtype)

def _mapDataciteItemized (metadata):
  return KernelMetadata(
    creator=_get(metadata, "datacite.creator"),
    title=_get(metadata, "datacite.title"),
    publisher=_get(metadata, "datacite.publisher"),
    date=_get(metadata, "datacite.publicationyear"),
    type=_get(metadata, "datacite.resourcetype"))

_rootTagRE =\
  re.compile("{(http://datacite\.org/schema/kernel-[^}]*)}resource$")

def _text (n):
  t = n.text
  if t == None: return None
  t = t.strip()
  if t != "":
    return t
  else:
    return None

def _mapDatacite (metadata):
  if _get(metadata, "datacite"):
    try:
      root = util.parseXmlString(_get(metadata, "datacite"))
      m = _rootTagRE.match(root.tag)
      assert m != None
      ns = { "N": m.group(1) }
      # Concatenate all creators.
      creator = " ; ".join(_text(n) for n in\
        root.xpath("N:creators/N:creator/N:creatorName", namespaces=ns)\
        if _text(n) != None)
      if creator == "": creator = None
      # Take the first title only.
      l = root.xpath("N:titles/N:title", namespaces=ns)
      if len(l) > 0:
        title = _text(l[0])
      else:
        title = None
      l = root.xpath("N:publisher", namespaces=ns)
      if len(l) > 0:
        publisher = _text(l[0])
      else:
        publisher = None
      l = root.xpath("N:publicationYear", namespaces=ns)
      if len(l) > 0:
        date = _text(l[0])
      else:
        date = None
      l = root.xpath("N:resourceType", namespaces=ns)
      if len(l) > 0:
        if l[0].attrib.get("resourceTypeGeneral", "").strip() != "":
          type = l[0].attrib["resourceTypeGeneral"].strip()
          if _text(l[0]) != None: type += "/" + _text(l[0])
        else:
          type = None
      else:
        type = None
      return KernelMetadata(creator, title, publisher, date, type)
    except:
      return _mapDataciteItemized(metadata)
  else:
    return _mapDataciteItemized(metadata)

def _mapCrossref (metadata):
  if _get(metadata, "crossref"):
    try:
      return _mapDatacite({ "datacite":
        datacite.crossrefToDatacite(_get(metadata, "crossref")) })
    except:
      return KernelMetadata()
  else:
    return KernelMetadata()

def map (metadata, profile=None):
  """
  Given 'metadata', a dictionary of citation metadata, returns mapped
  kernel metadata encapsulated in a KernelMetadata object (defined in
  this module).  If 'profile' is None, the metadata profile to use is
  determined from any _profile or _p field in the metadata dictionary;
  the profile defaults to "erc".  Note that this function is forgiving
  in nature, and does not raise exceptions.
  """
  if profile == None: profile = _get(metadata, "_profile", "_p")
  if profile == "dc":
    return _mapDublinCore(metadata)
  elif profile == "datacite":
    return _mapDatacite(metadata)
  elif profile == "crossref":
    return _mapCrossref(metadata)
  else:
    return _mapErc(metadata)
