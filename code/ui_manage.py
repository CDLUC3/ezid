import ui_common as uic
from django.shortcuts import render_to_response

d = { 'menu_item' : 'ui_manage.null'}

def index(request):
  d['menu_item'] = 'ui_manage.index'
  return render_to_response('manage/index.html', d)