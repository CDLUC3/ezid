import ui_common as uic
from django.shortcuts import render_to_response, redirect

d = { 'menu_item' : 'ui_demo.null'}

def index(request):
  return redirect("ui_demo.simple")
  d['menu_item'] = 'ui_demo.index'
  return uic.render(request, 'create/index', d)

def simple(request):
  d['menu_item'] = 'ui_demo.simple'
  return uic.render(request, 'create/simple', d)

def advanced(request):
  d['menu_item'] = 'ui_demo.advanced'
  return uic.render(request, 'create/advanced', d)