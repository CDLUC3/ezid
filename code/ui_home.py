from django.shortcuts import render_to_response
from django.conf import settings
from django.template import loader
import ui_common as uic

def index(request):
  d = { 'menu_item' : 'ui_home.index'}
  d['ezid_home_url'] = "http://" + request.get_host() +"/"
  d['prefixes'] = sorted(uic.testPrefixes, key=lambda p: p['namespace'].lower())
  return uic.render(request, 'index', d)

def learn(request):
  d = { 'menu_item' : 'ui_home.learn' }
  return uic.render(request, 'learn/index', d)

def crossref_faq(request):
  d = { 'menu_item' : 'ui_home.learn' }
  return uic.render(request, 'info/crossref_faq', d)

def id_basics(request):
  d = { 'menu_item' : 'ui_home.learn' }
  return uic.render(request, 'info/id_basics', d)

def suffix_passthrough(request):
  d = { 'menu_item' : 'ui_home.learn' }
  return uic.render(request, 'info/suffix_passthrough', d)

def no_menu(request, template_name):
  d = {'menu_item' : 'ui_home.null'}
  try:
    loader.get_template('info/' + template_name + ".html")
  except:
    return uic.error(request, 404)
  return uic.render(request, 'info/' + template_name, d)

