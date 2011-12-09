from django.shortcuts import render_to_response
import ui_common as uic

d = { 'menu_item' : 'ui_home.null'}

def index(request):
  d['menu_item'] = 'ui_home.index'
  return render_to_response('home/index.html', d)

def community(request):
  d['menu_item'] = 'ui_home.community'  
  return render_to_response('home/community.html', d)

def documentation(request):
  d['menu_item'] = 'ui_home.documentation'
  return render_to_response('home/documentation.html', d)

def outreach(request):
  d['menu_item'] = 'ui_home.outreach' 
  return render_to_response('home/outreach.html', d)

def pricing(request):
  d['menu_item'] = 'ui_home.pricing' 
  return render_to_response('home/pricing.html', d)

def understanding(request):
  d['menu_item'] = 'ui_home.understanding' 
  return render_to_response('home/understanding.html', d)

def why(request):
  d['menu_item'] = 'ui_home.why'
  return render_to_response('home/why.html', d)