import ui_common as uic
from django.shortcuts import redirect
import django.contrib.messages
import metadata
import ezid
import ui_create

def index(request):
  d = { 'menu_item' : 'ui_demo.index' }
  return redirect("ui_demo.simple")
  return uic.render(request, 'create/index', d)

def simple(request):
  d = { 'menu_item' :'ui_demo.simple' }
  d['prefixes'] = sorted(uic.testPrefixes, key=lambda p: p['prefix']) #must be done before calliung form processing
  r = ui_create.simple_form_processing(request, d)
  if r == 'bad_request':
    uic.badRequest()
  elif r.startswith('created_identifier:'):
    return redirect("ui_manage.details", r.split()[1])
  else:
    return uic.render(request, 'demo/simple', d)

def advanced(request):
  d = { 'menu_item' : 'ui_demo.advanced' }
  
  d['prefixes'] = sorted(uic.testPrefixes, key=lambda p: p['prefix']) #must be done before calling form processing
  r = ui_create.advanced_form_processing(request, d)
  if r == 'bad_request':
    uic.badRequest()
  elif r.startswith('created_identifier:'):
    return redirect("ui_manage.details", r.split()[1])
  else:
    return uic.render(request, 'demo/advanced', d)
