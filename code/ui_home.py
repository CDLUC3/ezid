from django.shortcuts import render_to_response
import ui_common as uic

d = { 'menu_item' : 'ui_home.null'}

def index(request):
  d['menu_item'] = 'ui_home.index'
  return uic.render(request, 'home/index', d)

def community(request):
  d['menu_item'] = 'ui_home.community'  
  return uic.render(request, 'home/community', d)

def documentation(request):
  d['menu_item'] = 'ui_home.documentation'
  return uic.render(request, 'home/documentation', d)

def outreach(request):
  d['menu_item'] = 'ui_home.outreach' 
  return uic.render(request, 'home/outreach', d)

def pricing(request):
  d['menu_item'] = 'ui_home.pricing' 
  return uic.render(request, 'home/pricing', d)

def understanding(request):
  d['menu_item'] = 'ui_home.understanding' 
  return uic.render(request, 'home/understanding', d)

def why(request):
  d['menu_item'] = 'ui_home.why'
  return uic.render(request, 'home/why', d)