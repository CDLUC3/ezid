# =============================================================================
#
# EZID :: ui_support :: reporting.py
#
# Gives views a way to generate reports for display without
# clogging the views with excessive code.
#
# The methods in the class generally return dictionaries with
# specific information at some level.
#
# A month-by-month table has a list of dictionaries with
# month included as well as ID type totals and percentages
# of ids that have metadata.
# example: {  'month': '2012-03', \
#             'DOI': '10,845', 'DOI_percent': '6%', \
#             'ARK': '17,987', 'ARK_percent': '6%', \
#             'URN': '0', 'URN_percent': '0%'}
#
# For totals, no month is given but id type totals,
# percentages with metadata and grand totals are given (and percent of metadata).
# example: { 'DOI': '120,512', 'DOI_percent': '88%', \
#            'ARK': '153,409', 'ARK_percent': '53%', \
#            'URN': '1', 'URN_percent': '0%', \
#            'total': '273,922', 'total_percent': '68%' }
# 
# Author:
#   Scott Fisher <sfisher@ucop.edu>
#
# License:
#   Copyright (c) 2013, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import stats
import datetime

class Report:
  #Generate a report for user and group (or None, None) for all""
  
  def __init__(self, user_id, group_id):
    self.user_id = user_id
    self.group_id = group_id
    return
  
  def full_table(self):
    """Create a stats table for display"""
    s = stats.getStats()
    months = _month_range_for_display(self.user_id, self.group_id)
    rows =[]
    
    id_types = ['ARK', 'DOI', 'URN']
    tallies = {'ARK': 0, 'DOI': 0, 'URN': 0}
    meta_tallies = {'ARK': 0.0, 'DOI': 0.0, 'URN': 0.0}
    
    for month in months:
      a={}
      a['month'] = month
      for id_type in id_types:
        temp = _number_and_percent(s, month, self.user_id, self.group_id, id_type)
        a[id_type] = temp[0]
        a[id_type + '_percent'] = temp[1]
      rows.append(a)
    return rows
  
  def totals(self):
    """Get totals for each identifier type, percent and grand totals"""
    s = stats.getStats()
    id_types = ['ARK', 'DOI', 'URN']
    a={}
    for id_type in id_types:
      temp = _number_and_percent(s, None, self.user_id, self.group_id, id_type)
      a[id_type] = temp[0]
      a[id_type + '_percent'] = temp[1]
    
    temp = _number_and_percent(s, None, self.user_id, self.group_id, None)
    a['total'] = temp[0]
    a['total_percent'] = temp[1]
    return a
  
  @staticmethod
  def computeTime():
    return _computeTime()
  
  @staticmethod
  def year_date_range_text():
    months = _last_year_date_range()
    return "Totals from " + months[0] + " through " + months[-1]
  
  def year_totals(self):
    months = _last_year_date_range()
    return _date_totals(months, self.user_id, self.group_id)
  
  def year_table(self):
    """creates table for the previous year (only whole months
    for which stats have been calculated)"""
    s = stats.getStats()
    months = _last_year_date_range()

    rows =[]
    
    id_types = ['ARK', 'DOI', 'URN']
    tallies = {'ARK': 0, 'DOI': 0, 'URN': 0}
    meta_tallies = {'ARK': 0.0, 'DOI': 0.0, 'URN': 0.0}
    
    for month in months:
      a={}
      a['month'] = month
      for id_type in id_types:
        temp = _number_and_percent(s, month, self.user_id, self.group_id, id_type)
        a[id_type] = temp[0]
        a[id_type + '_percent'] = temp[1]
      rows.append(a)
    return rows


#helper functions
def _computeTime():
  """returns the computetime as a datetime"""
  s = stats.getStats()
  return datetime.datetime.fromtimestamp(s.getComputeTime())

def _month_range_for_display(user, group):
  """
  Produces a list of year-month strings which goes from the earliest
  data available for the user, group specified (use None for none) until now.
  """
  dates = _get_month_range(datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime.now())
  s = stats.getStats()
  num = None
  for date in dates:
    num = s.query((date.strftime("%Y-%m"), user, group, None, None), False)
    if num > 0: break
  if date.strftime("%Y-%m") == datetime.datetime.now().strftime("%Y-%m") and num < 1:
    return []
  return [x.strftime("%Y-%m") for x in _get_month_range(date, datetime.datetime.now())]
  
def _get_month_range(dt1, dt2):
  """
  Creates a month range from the month/year of date1 to month/year of date2
  """
  start_month=dt1.month
  end_months=(dt2.year-dt1.year)*12 + dt2.month+1
  dates=[datetime.datetime(year=yr, month=mn, day=1) for (yr, mn) in (
          ((m - 1) / 12 + dt1.year, (m - 1) % 12 + 1) for m in range(start_month, end_months)
      )]
  return dates

def _insertCommas(n):
  """Format a number with commas"""
  s = ""
  while n >= 1000:
    n, r = divmod(n, 1000)
    s = ",%03d%s" % (r, s)
  return "%d%s" % (n, s)

def _monthdelta(date, delta):
  """Counting back by months"""
  m, y = (date.month+delta) % 12, date.year + ((date.month)+delta-1) // 12
  if not m: m = 12
  d = min(date.day, [31,
      29 if y%4==0 and not y%400==0 else 28,31,30,31,30,31,31,30,31,30,31][m-1])
  return date.replace(day=d,month=m, year=y)

def _number_and_percent(stats_obj, month, user_id, group_id, id_type, useLocalNames = False):
  """gets number and percent from stats_obj for month, user_id, group_id, id_type, useLocalNames.
  See stats.query for fuller explanation"""
  ids = stats_obj.query((month, user_id, group_id, id_type, None), useLocalNames)
  ids_w_meta = float(stats_obj.query((month, user_id, group_id, id_type, "True"), useLocalNames))
  if ids == 0:
    percent_meta = "0%"
  else:
    percent_meta = str(int((ids_w_meta / ids * 100))) + "%"
  ids = _insertCommas(ids)
  return (ids, percent_meta,)

def _last_year_date_range():
  """gets the list of dates for the last year of full
  months of calculated stats"""
  s = stats.getStats()
  last_calc = _computeTime()
  dt_start = datetime.datetime(last_calc.year - 1, last_calc.month, last_calc.day)
  dt_end = _monthdelta(last_calc, -1)
  return [x.strftime("%Y-%m") for x in _get_month_range(dt_start, dt_end)]

def _date_totals(date_list, user, group):
  """get totals for date list (each list date in %Y-%m format), need this
  function to total since the stats class doesn't do date ranges, afaik."""
  s = stats.getStats()
  tot = 0
  meta = 0
  id_types = ['ARK', 'DOI', 'URN']
  #set all id_types in dict to zero
  id_totals = dict((key, 0) for key in id_types)
  id_meta = dict((key, 0) for key in id_types)
  
  for month in date_list:
    #totals for all IDs for month
    tot = tot + s.query((month, user, group, None, None), False)
    meta = meta + s.query((month, user, group, None, "True"), False)
    #totals for each ID type for month
    for t in id_types:
      id_totals[t] = id_totals[t] + s.query((month, user, group, t, None), False)
      id_meta[t] = id_meta[t] + s.query((month, user, group, t, "True"), False)

  return_vals = {'total' : _insertCommas(tot) }
  
  for t in id_types:
    return_vals[t] = _insertCommas(id_totals[t])
    if id_totals[t] == 0:
      return_vals[t+'_percent'] = '0%'
    else:
      return_vals[t+'_percent'] = str(int((float(id_meta[t]) / id_totals[t] * 100.0))) + "%"
  if tot == 0:
    return_vals['total_percent'] = '0%'
  else:
    return_vals['total_percent'] = str(int((float(meta) / tot * 100.0))) + "%"
  
  return return_vals