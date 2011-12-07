from django.shortcuts import render_to_response
import ui_common


d = {'1_menu': 'home'}

def index(request):
  d['2_menu'] = 'index'
  return render_to_response('home/index.html', d)

def community(request):
  d['2_menu'] = 'community'  
  return render_to_response('home/community.html', d)

def documentation(request):
  d['2_menu'] = 'documentation' 
  return render_to_response('home/documentation.html', d)

def outreach(request):
  d['2_menu'] = 'outreach' 
  return render_to_response('home/outreach.html', d)

def pricing(request):
  d['2_menu'] = 'pricing' 
  return render_to_response('home/pricing.html', d)

def understanding(request):
  d['2_menu'] = 'understanding' 
  return render_to_response('home/understanding.html', d)

def why(request):
  d['2_menu'] = 'why'
  return render_to_response('home/why.html', d)