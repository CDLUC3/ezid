import ui_common as uic
from django.shortcuts import render_to_response

d = { 'menu_item' : 'ui_lookup.null'}

def index(request):
  d['menu_item'] = 'ui_lookup.index'
  return render_to_response('lookup/index.html', d)

