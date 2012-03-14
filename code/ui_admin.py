import ui_common as uic
import django.contrib.messages
import os
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
  d = { 'menu_item' :  'ui_admin.system_status' }
  return uic.render(request, 'admin/system_status', d)

def alert_message(request):
  d = { 'menu_item' : 'ui_admin.alert_message' }
  global alertMessage
  if request.method == "POST":
    if 'remove_it' in request.POST and request.POST['remove_it'] == 'remove_it':
      if os.path.exists(os.path.join(django.conf.settings.SITE_ROOT, "db","alert_message")):
        os.remove(os.path.join(django.conf.settings.SITE_ROOT, "db",
                               "alert_message"))
      alertMessage = ''
      django.contrib.messages.success(request, "Message removed. You must reload EZID before this message disappears.")
    elif 'message' in request.POST:
      m = request.POST["message"].strip()
      f = open(os.path.join(django.conf.settings.SITE_ROOT, "db",
        "alert_message"), "w")
      f.write(m)
      f.close()
      alertMessage = m
      django.contrib.messages.success(request, "Message updated. You must reload EZID before this message will appear.")
  return uic.render(request, 'admin/alert_message', d)