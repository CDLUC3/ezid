from django.shortcuts import render_to_response

d = { 'menu_item' : 'ui_demo.null'}

def index(request):
  d['menu_item'] = 'ui_demo.index'
  return render_to_response('create/index.html', d)

def simple(request):
  d['menu_item'] = 'ui_demo.simple'
  return render_to_response('create/simple.html', d)

def advanced(request):
  d['menu_item'] = 'ui_demo.advanced'
  return render_to_response('create/advanced.html', d)