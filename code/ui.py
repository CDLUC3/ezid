# =============================================================================
#
# EZID :: ui.py
#
# Selected User interface things left over from ui.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2010, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import ui_common as uic
import django.conf
import django.contrib.messages
import django.http
import django.template
import django.template.loader
import errno
import os
import re
import time
import urllib

import ezid
import datacite
import metadata

def doc (request):
  """
  Renders UTF-8 encoded HTML documentation.
  """
  if request.method != "GET": return uic.methodNotAllowed()
  assert request.path.startswith("/ezid/doc/")
  file = os.path.join(django.conf.settings.PROJECT_ROOT, "doc",
    request.path[10:])
  if os.path.exists(file):
    f = open(file)
    content = f.read()
    f.close()
    # If the filename of the requested document has what looks to be a
    # version indicator, attempt to load the unversioned (i.e.,
    # latest) version of the document.  Then, if the requested
    # document is not the latest version, add a warning.
    m = re.match("(.*/\w+)\.\w+\.html$", file)
    if m:
      uvfile = m.group(1) + ".html"
      if os.path.exists(uvfile):
        f = open(uvfile)
        uvcontent = f.read()
        f.close()
        if content != uvcontent:
          content = re.sub("<!-- superseded warning placeholder -->",
            "<p class='warning'>THIS VERSION IS SUPERSEDED BY A NEWER " +\
            "VERSION</p>", content)
    return uic.staticHtmlResponse(content)
  else:
    return uic.error(404)

def tombstone (request):
  """
  Renders a tombstone (i.e., unavailable identifier) page.
  """
  if request.method != "GET": return uic.methodNotAllowed()
  assert request.path.startswith("/ezid/tombstone/id/")
  id = request.path[19:]
  r = ezid.getMetadata(id)
  if type(r) is str:
    django.contrib.messages.error(request, uic.formatError(r))
    return uic.redirect("/ezid/")
  s, m = r
  if "_ezid_role" in m and ("auth" not in request.session or\
    request.session["auth"].user[0] != uic.adminUsername):
    # Special case.
    django.contrib.messages.error(request, "Unauthorized.")
    return uic.redirect("/ezid/")
  assert s.startswith("success:")
  id = s[8:].strip()
  if not m["_status"].startswith("unavailable"):
    return uic.redirect("/ezid/id/%s" % urllib.quote(id, ":/"))
  if "|" in m["_status"]:
    reason = "Not available: " + m["_status"].split("|", 1)[1].strip()
  else:
    reason = "Not available"
  htmlMode = False
  if m["_profile"] == "datacite" and "datacite" in m:
    md = datacite.dcmsRecordToHtml(m["datacite"])
    if md: htmlMode = True
  if not htmlMode:
    # This echoes the Merritt hack above.
    if m["_profile"] == "erc" and m.get("erc", "").strip() != "":
      md = [{ "label": "ERC", "value": m["erc"].strip() }]
    else:
      p = metadata.getProfile(m["_profile"])
      if not p: p = metadata.getProfile("erc")
      md = []
      for e in p.elements:
        if "." not in e.name: continue
        v = m.get(e.name, "").strip()
        md.append({ "label": e.displayName,
          "value": v if v != "" else "(no value)" })
  return uic.render(request, "tombstone", { "identifier": id,
    "identifierLink": "/ezid/id/%s" % urllib.quote(id, ":/"),
    "reason": reason, "htmlMode": htmlMode, "metadata": md })
