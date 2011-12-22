import ui_common as uic
from django.shortcuts import render_to_response, redirect
import metadata

d = { 'menu_item' : 'ui_create.null'}

def index(request):
  return redirect("ui_create.simple")
  d['menu_item'] = 'ui_create.index'
  return uic.render(request, 'create/index', d)

def simple(request):
  d['menu_item'] = 'ui_create.simple'
  d['current_profile'] = metadata.getProfile('dc')
  d['internal_profile'] = metadata.getProfile('internal')
  return uic.render(request, 'create/simple', d)

def advanced(request):
  d['menu_item'] = 'ui_create.advanced'
  return uic.render(request, 'create/advanced', d)