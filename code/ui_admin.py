import ui_common as uic
import userauth
import ezidapp.models
import stats
from datetime import datetime
import ui_search 
from collections import *
import csv
import StringIO
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
  d['heading_user_display'] = user.displayName + "'s EZID " + _("Dashboard")
  d['display_adminlink'] = user.isSuperuser 
  REQUEST = request.GET if request.method == "GET" else request.POST
  if not('owner_selected' in REQUEST) or REQUEST['owner_selected'] == '':
    d['owner_selected'] = None if user.isSuperuser \
      else "realm_" + user.realm.name if user.isRealmAdministrator \
      else "group_" + user.group.groupname if user.isGroupAdministrator \
      else "user_" + user.username
  else:
   d['owner_selected'] = REQUEST['owner_selected'] 
  d['owner_names'] = uic.owner_names(user, "dashboard")
  d = _getUsage(request, user, d)
  d['ajax'] = False

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
  table = [] 
  s = stats.getStats()
  user_id, group_id, realm_id = uic.getOwnerOrGroupOrRealm(d['owner_selected'])
  if realm_id != None:
    realm = ezidapp.models.StoreRealm.objects.get(name=realm_id)
    for g in realm.groups.all():
      for u in g.users.all(): 
        table += s.getTable(owner=u.username)
  elif group_id != None:
    table = s.getTable(group=group_id)
  else:
    if user_id == 'all': user_id = None
    table = s.getTable(owner=user_id)
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

def csvStats (request):
  """
  Returns all statistics to which a user is entitled as a CSV file.
  'requestor' is the user, and should be a StoreUser object.  The
  statistics include those for the requestor; and all users (if the
  requestor is a superuser) or all users in the requestor's realm (if
  the requestor is a realm administrator) or all users in the
  requestor's group (if the requestor is a group administrator); plus
  any users the requestor is a proxy for.  The CSV file is returned as
  a single string.  The columns are:

  owner
  ownergroup
  month
  ARKs with metadata
  ARKs without metadata
  total ARKs
  DOIs with metadata
  DOIs without metadata
  total DOIs

  Rows are grouped by user; the order of users in the CSV file is
  undefined.  For a given user, rows are ordered by month, and the
  rows are complete with respect to the range of months, as described
  in stats.Stats.getTable().
  """
  requestor = userauth.getUser(request)
  users = set([requestor])
  if requestor.isSuperuser:
    for u in ezidapp.models.StoreUser.objects.all(): users.add(u)
  elif requestor.isRealmAdministrator:
    for g in requestor.realm.groups.all():
      for u in g.users.all(): users.add(u)
  elif requestor.isGroupAdministrator:
    for u in requestor.group.users.all(): users.add(u)
  for u in requestor.proxy_for.all(): users.add(u)
  s = stats.getStats()
  f = StringIO.StringIO()
  w = csv.writer(f)
  w.writerow(["owner", "ownergroup", "month", "ARKs with metadata",
    "ARKs without metadata", "ARKs total", "DOIs with metadata",
    "DOIs without metadata", "DOIs total"])
  for u in users:
    for r in s.getTable(owner=u.pid, useLocalNames=False):
      outputRow = [u.username, u.group.groupname, r[0]]
      for type in ["ARK", "DOI"]:
        t = 0
        for hasMetadata in ["True", "False"]:
          v = r[1].get((type, hasMetadata), 0)
          outputRow.append(str(v))
          t += v
        outputRow.append(str(t))
      w.writerow(outputRow)
  fn = "EZID_" + requestor.username + datetime.now().strftime("%Y%m%d-%H%M%S")
  return uic.csvResponse(f.getvalue(), fn) 
