import ui_common as uic
import django.contrib.messages
import os
import ezidadmin
import config
from django.shortcuts import render_to_response, redirect

def index(request):
  d = { 'menu_item' : 'ui_admin.index'}
  return redirect("ui_admin.usage")
  return uic.render(request, 'admin/index', d)

def usage(request):
  d = { 'menu_item' : 'ui_admin.usage'}
  return uic.render(request, 'admin/usage', d)

def manage_users(request):
  d = { 'menu_item' : 'ui_admin.manage_users' }
  return uic.render(request, 'admin/manage_users', d)

def manage_groups(request):
  d = { 'menu_item' : 'ui_admin.manage_groups' }
  return uic.render(request, 'admin/manage_groups', d)

def system_status(request):
  if "auth" not in request.session or request.session["auth"].user[0] != uic.adminUsername:
    return uic.unauthorized()
  d = { 'menu_item' :  'ui_admin.system_status' }
  d['status_list'] = ezidadmin.systemStatus(None)
  d['js_ids'] =  '[' + ','.join(["'" + x['id'] + "'" for x in d['status_list']]) + ']'
  if request.method == "POST":
    config.load()
    request.session.flush()
    django.contrib.messages.success(request, "EZID reloaded.")
    django.contrib.messages.success(request, "You have been logged out.")
    return uic.redirect("/ezid/")
  return uic.render(request, 'admin/system_status', d)

def ajax_system_status(request):
  if "auth" not in request.session or request.session["auth"].user[0] != uic.adminUsername:
    return uic.unauthorized()
  if request.method != "GET": return uic.methodNotAllowed()
  if "id" in request.GET:
    return uic.plainTextResponse(request.GET["id"] + ":" + ezidadmin.systemStatus(request.GET["id"]))

def alert_message(request):
  if "auth" not in request.session or request.session["auth"].user[0] != uic.adminUsername:
    return uic.unauthorized()
  d = { 'menu_item' : 'ui_admin.alert_message' }
  print 'uic.alertMessage=' + uic.alertMessage
  if request.method == "POST":
    if 'remove_it' in request.POST and request.POST['remove_it'] == 'remove_it':
      if os.path.exists(os.path.join(django.conf.settings.SITE_ROOT, "db","alert_message")):
        os.remove(os.path.join(django.conf.settings.SITE_ROOT, "db",
                               "alert_message"))
      #global alertMessage  
      uic.alertMessage = ''
      django.contrib.messages.success(request, "Message removed.")
    elif 'message' in request.POST:
      m = request.POST["message"].strip()
      f = open(os.path.join(django.conf.settings.SITE_ROOT, "db",
        "alert_message"), "w")
      f.write(m)
      f.close()
      #global alertMessage
      uic.alertMessage = m
      django.contrib.messages.success(request, "Message updated.")
  return uic.render(request, 'admin/alert_message', d)