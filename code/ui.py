import ui_common as uic
import django.conf
import django.contrib.messages
import django.core.mail
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

def ajax_hide_alert(request):
  request.session['hide_alert'] = True
  return uic.plainTextResponse('Ok')

def contact(request):
  d = { 'menu_item': 'ui_null.null'}
  d['heard']      =   ( ("website", "University website"), \
                        ("conference", "Conference"), \
                        ("colleagues", "Colleagues"), \
                        ("webinar", "Webinar"), \
                        ("other", "Other") )
  if request.method == "GET":
    d['your_name'], d['email'], d['affiliation'], d['comment'], d['hear_about'] = '', '', '', '', ''
  elif request.method == "POST":
    P = request.POST
    for i in ['your_name', 'email', 'comment', 'hear_about']:
      if not i in P:
        d['your_name'], d['email'], d['affiliation'], d['comment'], d['hear_about'] = '', '', '', '', ''
        return uic.render(request, 'contact', d)
    d.update(uic.extract(request.POST, ['your_name', 'email', 'affiliation', 'comment', 'hear_about']))
    errored = False
    if P['your_name'] == '':
      django.contrib.messages.error(request, "Please fill in your name.")
      errored = True
    if P['email'] == '' or not re.match('^.+\@.+\..+$', P['email']):
      django.contrib.messages.error(request, "Please fill in a valid email address.")
      errored = True
    if P['comment'].strip() == '':
      django.contrib.messages.error(request, "Please fill in a question or comment.")
      errored = True
    if errored:
      return uic.render(request, 'contact', d)
    if not 'url' in P or P['url'] != '':
      #url is hidden.  If it's filled in then probably a spam bot
      return uic.render(request, 'contact', d)
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
      django.core.mail.send_mail(title, message,
        P['email'], emails)

      django.contrib.messages.success(request, "Message sent")
      d['your_name'], d['email'], d['affiliation'], d['comment'], d['hear_about'] = '', '', '', '', ''
    except:
      django.contrib.messages.error(request, "There was a problem sending your email")
      return uic.render(request, 'contact', d)
    #django.core.mail.send_mail("EZID password reset request", message,
    #  django.conf.settings.SERVER_EMAIL, [emailAddress])
  return uic.render(request, 'contact', d)

def __emails(request):
  """gets email addresses based on environment settings and also current domain name"""
  host = request.META.get("HTTP_HOST", "default")
  if host not in django.conf.settings.LOCALIZATIONS: host = "default"
  return django.conf.settings.LOCALIZATIONS[host][1]

def doc (request):
  """
  Renders UTF-8 encoded HTML documentation.
  """
  if request.method != "GET": return uic.methodNotAllowed()
  assert request.path_info.startswith("/doc/")
  file = os.path.join(django.conf.settings.PROJECT_ROOT, "doc",
    request.path_info[5:])
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
    if file.endswith(".html"):
      return uic.staticHtmlResponse(content)
    else:
      return uic.staticTextResponse(content)
  else:
    return uic.error(404)

def tombstone (request):
  """
  Renders a tombstone (i.e., unavailable identifier) page.
  """
  if request.method != "GET": return uic.methodNotAllowed()
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
    "identifierLink": "/id/%s" % urllib.quote(id, ":/"),
    "reason": reason, "htmlMode": htmlMode, "metadata": md })
