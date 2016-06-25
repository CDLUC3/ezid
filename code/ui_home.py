from django.template import loader
import ui_common as uic
from django.shortcuts import redirect
import ui_create
import urllib

def index(request):
  if request.method not in ["GET", "POST"]:
    return uic.methodNotAllowed(request)
  d = { 'menu_item' : 'ui_home.index'}
  d['prefixes'] = sorted(uic.testPrefixes, key=lambda p: p['namespace'].lower())
  d['form_placeholder']= True
  d = ui_create.simple_form(request, d)
  result = d['id_gen_result']
  if result == 'edit_page':
    return uic.render(request, 'index', d)  # ID Creation page 
  elif result == 'bad_request':
    return uic.badRequest(request)
  elif result.startswith('created_identifier:'):
    return redirect("/id/" + urllib.quote(result.split()[1], ":/"))   # ID Details page

def learn(request):
  if request.method != "GET": return uic.methodNotAllowed(request)
  d = { 'menu_item' : 'ui_home.learn' }
  return uic.render(request, 'learn', d)

def crossref_faq(request):
  if request.method != "GET": return uic.methodNotAllowed(request)
  d = { 'menu_item' : 'ui_home.learn' }
  return uic.render(request, 'info/crossref_faq', d)

def id_basics(request):
  if request.method != "GET": return uic.methodNotAllowed(request)
  d = { 'menu_item' : 'ui_home.learn' }
  return uic.render(request, 'info/id_basics', d)

def id_concepts(request):
  if request.method != "GET": return uic.methodNotAllowed(request)
  d = { 'menu_item' : 'ui_home.learn' }
  return uic.render(request, 'info/id_concepts', d)

def open_source(request):
  if request.method != "GET": return uic.methodNotAllowed(request)
  d = { 'menu_item' : 'ui_home.learn' }
  return uic.render(request, 'info/open_source', d)

def suffix_passthrough(request):
  if request.method != "GET": return uic.methodNotAllowed(request)
  d = { 'menu_item' : 'ui_home.learn' }
  return uic.render(request, 'info/suffix_passthrough', d)

def no_menu(request, template_name):
  if request.method != "GET": return uic.methodNotAllowed(request)
  d = {'menu_item' : 'ui_home.null'}
  try:
    loader.get_template('info/' + template_name + ".html")
  except:
    return uic.error(request, 404)
  return uic.render(request, 'info/' + template_name, d)

