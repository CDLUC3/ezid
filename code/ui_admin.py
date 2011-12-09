import ui_common as uic
from django.shortcuts import render_to_response, redirect

d = { 'menu_item' : 'ui_admin.null'}

def index(request):
  return redirect("ui_admin.usage")
  d['menu_item'] = 'ui_admin.index'
  return render_to_response('admin/index.html', d)

def usage(request):
  d['menu_item'] = 'ui_admin.usage'
  return render_to_response('admin/usage.html', d)

def manage_users(request):
  d['menu_item'] = 'ui_admin.manage_users'
  return render_to_response('admin/manage_users.html', d)

def manage_groups(request):
  d['menu_item'] = 'ui_admin.manage_groups'
  return render_to_response('admin/manage_groups.html', d)

def system_status(request):
  d['menu_item'] = 'ui_admin.system_status'
  return render_to_response('admin/system_status.html', d)

def alert_message(request):
  d['menu_item'] = 'ui_admin.alert_message'
  return render_to_response('admin/alert_message.html', d)