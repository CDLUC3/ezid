import ui_common as uic
import django.contrib.messages

def index(request):
  d = { 'menu_item' : 'ui_search.index' }
  if request.method == "GET":
    return uic.render(request, 'search/index', d)
  elif request.method == "POST":
    return uic.render(request, 'search/results', d)

def results(request):
  d = { 'menu_item' : 'ui_search.results' } 
  return uic.render(request, 'search/results', d)
