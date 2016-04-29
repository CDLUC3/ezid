import ui_common as uic
import ezidapp.models
import stats
import datetime

@uic.admin_login_required
def index(request, ssl=False):
  d = { 'menu_item' : 'ui_admin.index'}
  return uic.render(request, 'admin-old/index', d)

@uic.admin_login_required
def usage(request, ssl=False):
  d = { 'menu_item' : 'ui_admin.usage'}
  #make select list choices
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
    lastYear = table[-12:]
    d["lastYear"] = _computeTotals(lastYear)
    d["lastYearFrom"] = lastYear[0][0]
    d["lastYearTo"] = lastYear[-1][0]

  last_calc = datetime.datetime.fromtimestamp(s.getComputeTime())
  d['last_tally'] = last_calc.strftime('%B %d, %Y')
  return uic.render(request, 'admin-old/usage', d)

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
