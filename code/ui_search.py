import ui_common as uic
import django.contrib.messages
import form_objects
from django.utils.translation import ugettext as _

def index(request):
  d = { 'menu_item' : 'ui_search.index' }
  if request.method == "GET":
    d['form'] = form_objects.SearchForm() # Build an empty form
    return uic.render(request, 'search/index', d)
  elif request.method == "POST":
    d['form'] = form_objects.SearchForm(request.POST)
    if d['form'].is_valid():
      return uic.render(request, 'search/results', d)
    else:
      all_errors = ''
      errors = d['form'].errors['__all__']
      for e in errors:
        all_errors += e 
      django.contrib.messages.error(request, _("Could not complete search.   " + all_errors))
      return uic.render(request, 'search/index', d)

def results(request):
  d = { 'menu_item' : 'ui_search.results' } 
  return uic.render(request, 'search/results', d)
