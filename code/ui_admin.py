import ui_common as uic
import userauth
import ezidapp.models
import stats
from datetime import datetime
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
  owner_selected = ()
  d['display_adminlink'] = user.isRealmAdministrator or user.isSuperuser 
  REQUEST = request.GET if request.method == "GET" else request.POST
  if not('owner_selected' in REQUEST) or REQUEST['owner_selected'] == '':
    g = "group_"
    u = "user_"
    owner_selected = ('all', 'all') if user.isSuperuser else (g + user.group.pid, \
      g + user.group.groupname) if user.isGroupAdministrator else (u + user.pid, \
      u + user.username)
    # Set owner/group selector to pid 
    d['owner_selected'] = owner_selected[0]
    # ToDo: Make sure this works for Realm Admin and picking Groups
  else:
   d['owner_selected'] = REQUEST['owner_selected'] 
  d['owner_names'] = uic.owner_names(user, "dashboard")
  d = _getUsage(request, user, d)
  d['ajax'] = False

  # Set owner/group selector to username
  d['owner_selected'] = owner_selected[1] if owner_selected else REQUEST['owner_selected'] 
  # Search:    ID Issues
  d = ui_search.search(d, request, NO_CONSTRAINTS, "issues")
  # UI Tables need data named uniquely to distinguish them apart
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

def _getUsage(request, user, d):
  user_id, group_id = uic.getOwnerOrGroup(d['owner_selected'])
  s = stats.getStats()
  table = s.getTable(owner=user_id, group=group_id, useLocalNames=False)
  all_months = _computeMonths(table)
  if len(all_months) > 0:
    d["totals"] = _computeTotals(table)
    month_earliest = table[0][0]
    month_latest = "%s-%s" % (datetime.now().year, datetime.now().month)
    d['months_all'] = [m[0] for m in table]
    default_table = table[-12:]
    REQUEST = request.GET if request.method == "GET" else request.POST
    d["month_from"] = REQUEST["month_from"] if "month_from" in REQUEST else default_table[0][0]
    d["month_to"] = REQUEST["month_to"] if "month_to" in REQUEST else default_table[-1][0]
    d["totals_by_month"] = _computeMonths(_getScopedRange(table, d['month_from'], d['month_to']))

  last_calc = datetime.fromtimestamp(s.getComputeTime())
  d['last_tally'] = last_calc.strftime('%B %d, %Y')
  return d

def _getScopedRange(table, mfrom, mto):
  ifrom = [i for i,d in enumerate(table) if d[0] == mfrom]
  ito = [i for i,d in enumerate(table) if d[0] == mto]
  return table[ifrom[0]:ito[0]+1]

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

