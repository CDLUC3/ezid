import ui_common as uic
import userauth
import ezidapp.models
import stats
import datetime
import ui_search 
from collections import *
from django.utils.translation import ugettext as _

NO_CONSTRAINTS = True 

@uic.user_login_required
def dashboard(request, ssl=False):
  """ 
  ID Issues and Crossref tables load for the first time w/o ajax
  All subsequent searches are done via ajax (ajax_dashboard_table method below)
  """
  d = { 'menu_item' : 'ui_admin.dashboard'}
  user = userauth.getUser(request)
  d['display_adminlink'] = user.isRealmAdministrator or user.isSuperuser 
  REQUEST = request.GET if request.method == "GET" else request.POST
  d['owner_selected'] = REQUEST['owner_selected'] if \
    'owner_selected' in REQUEST else user.username
  d['owner_names'] = uic.related_users(user)
  if user.isGroupAdministrator:
    d['group_admin'] = user.displayName + _("  (me)")
    if d['owner_selected'] == user.username:
      d['ownergroup_selected'] = user.group.groupname
  d = _getUsage(request, d)

  d['ajax'] = False
  # Search:    ID Issues
  d = ui_search.search(d, request, NO_CONSTRAINTS, "issues")
  # Tables need data named uniquely to distinguish them apart
  d['results_issues'] = d['results']
  d['total_pages_issues'] = d['total_pages']
  d['field_display_types_issues'] = d['field_display_types']
  d['fields_selected_issues'] = d['fields_selected']

  # Search:    Crossref Submission Status 
  d = ui_search.search(d, request, NO_CONSTRAINTS, "crossref")
  d['order_by'] = 'c_crossref_date'
  d['sort'] = 'asc'
  d['results_crossref'] = d['results']
  d['total_pages_crossref'] = d['total_pages']
  d['field_display_types_crossref'] = d['field_display_types']
  d['fields_selected_crossref'] = d['fields_selected']
  return uic.render(request, 'dashboard/index', d)

def ajax_dashboard_table(request):
  if request.is_ajax():
    user = userauth.getUser(request)
    G = request.GET
    d = {}
    d['owner_selected'] = G['owner_selected'] if 'owner_selected' in G else user.username
    d['p'] = G.get('p')
    if 'name' in G and d['p'] is not None and d['p'].isdigit():
      d['ajax'] = True
      d = ui_search.search(d, request, NO_CONSTRAINTS, G['name'])
      return uic.render(request, "dashboard/_" + G['name'], d)

def _getUsage(request, d):
  # ToDo: Merge into owner_selector
  users = ezidapp.models.StoreUser.objects.all().order_by("username")
  groups = ezidapp.models.StoreGroup.objects.all().order_by("groupname")
  user_choices = [("user_" + x.pid, x.username) for x in users]
  group_choices = [("group_" + x.pid, x.groupname) for x in groups]
  d['choices'] = [("all", "All EZID")] + [('',''), ('', '-- Groups --')] + \
      group_choices + [('',''), ('', '-- Users --')] + user_choices
      
  if request.method != "POST" or not('choice' in request.POST) or request.POST['choice'] == '':
    d['choice'] = 'all'
  else:
    d['choice'] = request.POST['choice']
    
  #query all
  user_id, group_id = None, None
  if d['choice'].startswith('user_'):
    user_id = d['choice'][5:]
  elif d['choice'].startswith('group_'):
    group_id = d['choice'][6:]
  
  s = stats.getStats()
  table = s.getTable(owner=user_id, group=group_id, useLocalNames=False)
  d["months"] = _computeMonths(table)
  if len(d["months"]) > 0:
    d["totals"] = _computeTotals(table)
    month_range = table[-12:]
    d["lastYear"] = _computeTotals(month_range)
    d["lastYearFrom"] = lastYear[0][0]
    d["lastYearTo"] = lastYear[-1][0]

  last_calc = datetime.datetime.fromtimestamp(s.getComputeTime())
  d['last_tally'] = last_calc.strftime('%B %d, %Y')

  # Used for totals of last 12 months. No longer used.
  # d['yearly'] = _year_totals(user_id, group_id, last_calc)
  
  return d

def _percent (m, n):
  if n == 0:
    return 0
  else:
    return m*100/n

def _insertCommas (n):
  s = ""
  while n >= 1000:
    n, r = divmod(n, 1000)
    s = ",%03d%s" % (r, s)
  return "%d%s" % (n, s)

def _computeMonths (table):
  months = []
  for month, d in table:
    months.append({ "month": month })
    for type in ["ARK", "DOI"]:
      total = d.get((type, "True"), 0) + d.get((type, "False"), 0)
      months[-1][type] = { "total": _insertCommas(total),
        "hasMetadataPercentage":\
        str(_percent(d.get((type, "True"), 0), total)) }
  return months[::-1]

def _computeTotals (table):
  if len(table) == 0: table = [("dummy", {})]
  data = {}
  for row in table:
    for type in ["ARK", "DOI"]:
      for hasMetadata in ["True", "False"]:
        t = (type, hasMetadata)
        data[t] = data.get(t, 0) + row[1].get(t, 0)
        data[("grand", hasMetadata)] =\
          data.get(("grand", hasMetadata), 0) + row[1].get(t, 0)
  totals = {}
  for type in ["ARK", "DOI", "grand"]:
    total = data[(type, "True")] + data[(type, "False")]
    totals[type] = { "total": _insertCommas(total),
      "hasMetadataPercentage": str(_percent(data[(type, "True")], total)) }
  return totals

