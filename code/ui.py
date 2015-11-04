import ui_common as uic
import django.conf
import django.contrib.messages
import django.core.mail
import django.http
import django.template
import django.template.loader
import form_objects
import errno
import os
import re
import time
import urllib

import ezid
import datacite
import metadata
from django.utils.translation import ugettext as _

def ajax_hide_alert(request):
  request.session['hide_alert'] = True
  return uic.plainTextResponse('Ok')

def contact(request):
  d = { 'menu_item': 'ui_null.contact'}
  if request.method == "POST":
    P = request.POST
    d['form'] = form_objects.ContactForm(P)
    if not 'url' in P or P['url'] != '':
      #url is hidden.  If it's filled in then probably a spam bot
      pass
    elif d['form'].is_valid():
      emails = __emails(request)
      title = "EZID contact form email"
      if 'HTTP_REFERER' in request.META:
        message = 'Sent FROM: ' + request.META['HTTP_REFERER'] +"\r\n\r\n"
      else:
        message = ''
        message += "Name: " + P['your_name'] + "\r\n\r\n" + \
          "Email: " + P['email'] + "\r\n\r\n"
      if 'affiliation' in P:
        message += "Institution: " +  P['affiliation'] + "\r\n\r\n"
        message += "Comment:\r\n" + P['comment'] + "\r\n\r\n" + \
          "Heard about from: " + P['hear_about']
      try:
        django.core.mail.send_mail(title, message, P['email'], emails)

        django.contrib.messages.success(request, _("Message sent"))
        d['form'] = form_objects.ContactForm() # Build an empty form
      except:
        django.contrib.messages.error(request, _("There was a problem sending your email"))
    elif not d['form'].is_valid() :
      django.contrib.messages.error(request, _("Form could not be sent. Please check \
        the highlighted field(s) below for details."))
      # fall through to re-render page; form already contains error info
  else:  # GET Request
    d['form'] = form_objects.ContactForm() # Build an empty form
  return uic.render(request, 'contact', d)

def __emails(request):
  """gets email addresses based on environment settings and also current domain name"""
  host = request.META.get("HTTP_HOST", "default")
  if host not in django.conf.settings.LOCALIZATIONS: host = "default"
  return django.conf.settings.LOCALIZATIONS[host][1]

def doc (request):
  """
  Renders UTF-8 encoded HTML documentation and plain text Python code
  files.
  """
  if request.method != "GET": return uic.methodNotAllowed(request)
  assert request.path_info.startswith("/doc/")
  file = request.path_info[5:]
  path = os.path.join(django.conf.settings.PROJECT_ROOT, "templates", "doc",
    file)
  if os.path.exists(path):
    if file.endswith(".html"):
      return uic.render(request, os.path.join("doc", file[:-5]),
        { "menu_item": "ui_home.learn" })
    else:
      f = open(path)
      content = f.read()
      f.close()
      return uic.staticTextResponse(content)
  else:
    return uic.error(request, 404)

def tombstone (request):
  """
  Renders a tombstone (i.e., unavailable identifier) page.
  """
  if request.method != "GET": return uic.methodNotAllowed(request)
  assert request.path_info.startswith("/tombstone/id/")
  id = request.path_info[14:]
  if "auth" in request.session:
    r = ezid.getMetadata(id, request.session["auth"].user,
      request.session["auth"].group)
  else:
    r = ezid.getMetadata(id)
  if type(r) is str:
    django.contrib.messages.error(request, uic.formatError(r))
    return uic.redirect("/")
  s, m = r
  assert s.startswith("success:")
  id = s[8:].strip()
  if not m["_status"].startswith("unavailable"):
    return uic.redirect("/id/%s" % urllib.quote(id, ":/"))
  if "|" in m["_status"]:
    # Translators: Output for tombstone page (unavailable IDs)
    reason = "_(Not available: )" + m["_status"].split("|", 1)[1].strip()
  else:
    reason = "_(Not available)"
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
    "identifierLink": "/id/%s" % urllib.quote(id, ":/"),
    "reason": reason, "htmlMode": htmlMode, "metadata": md })
