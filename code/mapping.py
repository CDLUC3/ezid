# =============================================================================
#
# EZID :: mapping.py
#
# Metadata mapping.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2012, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import lxml.etree
import re

import erc

def _get (d, *keys):
  for k in keys:
    if k in d: return d[k]
  return None

def _text (n):
  t = n.text
  if t is not None:
    t = t.strip()
    return t if len(t) > 0 else None
  else:
    return None

def _displayErcItemized (metadata):
  return (_get(metadata, "erc.who"), _get(metadata, "erc.what"), None,
    _get(metadata, "erc.when"))

def _displayErc (metadata):
  if "erc" in metadata and metadata["erc"].strip() != "":
    try:
      d = erc.parse(metadata["erc"])
      return (_get(d, "who"), _get(d, "what"), None, _get(d, "when"))
    except:
      return _displayErcItemized(metadata)
  else:
    return _displayErcItemized(metadata)

def _displayDublinCore (metadata):
  return (_get(metadata, "dc.creator"), _get(metadata, "dc.title"),
    _get(metadata, "dc.publisher"), _get(metadata, "dc.date"))

def _displayDataciteItemized (metadata):
  return (_get(metadata, "datacite.creator"), _get(metadata, "datacite.title"),
    _get(metadata, "datacite.publisher"),
    _get(metadata, "datacite.publicationyear"))

_rootTagRE =\
  re.compile("{(http://datacite\.org/schema/kernel-[^}]*)}resource$")

def _displayDatacite (metadata):
  if "datacite" in metadata:
    try:
      root = lxml.etree.XML(metadata["datacite"])
      m = _rootTagRE.match(root.tag)
      assert m != None
      ns = { "N": m.group(1) }
      # Concatenate all creators.
      creator = " ; ".join(_text(n) for n in\
        root.xpath("N:creators/N:creator/N:creatorName", namespaces=ns)\
        if _text(n) is not None)
      if len(creator) == 0: creator = None
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
        publicationYear = _text(l[0])
      else:
        publicationYear = None
      return (creator, title, publisher, publicationYear)
    except:
      return _displayDataciteItemized(metadata)
  else:
    return _displayDataciteItemized(metadata)

def getDisplayMetadata (metadata):
  """
  Given 'metadata', a dictionary of element (name, value) pairs,
  returns normalized kernel metadata.  Specifically, the return is a
  tuple (creator, title, publisher, date); each component of the tuple
  either has a nonempty value or is None.
  """
  p = _get(metadata, "_profile", "_p")
  if p == "dc":
    return _displayDublinCore(metadata)
  elif p == "datacite":
    return _displayDatacite(metadata)
  else:
    return _displayErc(metadata)
