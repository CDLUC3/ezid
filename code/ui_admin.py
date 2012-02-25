import ui_common as uic
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
  return uic.render(request, 'admin/alert_message', d)