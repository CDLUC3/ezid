import ui_common as uic
from django.shortcuts import redirect
import ui_create
import urllib
def index(request):
  d = { 'menu_item' : 'ui_home.learn' }
  return redirect("ui_demo.simple")
  return uic.render(request, 'create/index', d)

def simple(request):
  d = { 'menu_item' :'ui_home.learn' }
  d["testPrefixes"] = uic.testPrefixes
  d['prefixes'] = sorted(uic.testPrefixes, key=lambda p: p['namespace'].lower()) #must be done before calling form processing
  d = ui_create.simple_form_processing(request, d)
  result = d['id_gen_result']
  if result == 'edit_page':
    return uic.render(request, 'demo/simple', d)  # ID Creation page 
  elif result == 'bad_request':
    return uic.badRequest()
  elif result.startswith('created_identifier:'):
    return redirect("/id/" + urllib.quote(result.split()[1], ":/"))   # ID Details page

def advanced(request):
  d = { 'menu_item' : 'ui_home.learn' }
  d["testPrefixes"] = uic.testPrefixes
  d['prefixes'] = sorted(uic.testPrefixes, key=lambda p: p['namespace'].lower()) #must be done before calling form processing
  d = ui_create.adv_form(request, d)
  result = d['id_gen_result']
  if result == 'edit_page':
    return uic.render(request, 'demo/advanced', d)  # ID Creation page 
  elif result == 'bad_request':
    return uic.badRequest()
  elif result.startswith('created_identifier:'):
    return redirect("/id/" + urllib.quote(result.split()[1], ":/"))   # ID Details page
 
