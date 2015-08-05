import ui_common as uic
import django.contrib.messages

def index(request):
  d = { 'menu_item' : 'ui_search.index' } 
  return uic.render(request, 'search/index', d)
