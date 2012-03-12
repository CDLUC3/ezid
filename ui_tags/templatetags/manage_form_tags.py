from django import template
#from django.conf import settings
from django.utils.html import escape
from decorators import basictag
#from django.core.urlresolvers import reverse
#import pdb
import datetime
import urllib
from django.core.urlresolvers import reverse
import idmap
import itertools

register = template.Library()

@register.simple_tag 
def column_choices(field_order, fields_mapped, fields_selected, no_cols=3):
  """this only works when the following context variables are set from the django view:
  field_order is the ordered list of the fields
  fields_mapped is mapping of fields to texual names
  fields_selected is ordered list of selected fields"""
  items_per_col = (len(field_order) - 1 + no_cols) / no_cols
  col_arr = chunks(field_order, items_per_col) #divided into sub-lists for three columns
  return "<div class='chk_col'>" + "</div><div class='chk_col'>".join(['<br/>'.join(\
         [make_check_tag(y, fields_mapped, fields_selected) for y in x]) \
         for x in col_arr]) + '</div>'
  #this is the similified version of this nested list comprehension and join
  #return '<div>' + '</div><div>'.join(['<br/>'.join(testy(x)) for x in col_arr]) + '</div>' --backup copy
#def testy(my_list):
#  return [make_tag(y) for y in my_list]

def make_check_tag(item, friendly_names, selected):
  if item in selected:
    checked_str = " checked='checked' "
  else:
    checked_str = ""
  return "<input type='checkbox' id='" + escape(item) + "' name='" + escape(item) + "' value='t'" + checked_str + " \> " \
       + "<label for='" + escape(item) + "'>" + escape(friendly_names[item]) + "</label>"

@register.simple_tag   
def rewrite_hidden_except(request, field_order):
  exclude = field_order + ['submit_checks']
  hidden = ''
  for key, value in request.iteritems():
    if not (key in exclude):
      hidden += "<input type='hidden' name='" + escape(key) + "' value='" + escape(value) + "'/>"
  return hidden

@register.simple_tag
def header_row(request, fields_selected, fields_mapped, field_widths, order_by, sort):
  total_width = 0
  for item in fields_selected:
    total_width += field_widths[item]
  return "<tr class='headrow'>" + ''.join([("<th style='width:" + percent_width(field_widths[x], total_width) + \
                            "'>" + column_head(request, x, fields_mapped, order_by, sort) + "</th>"  ) \
          for x in fields_selected]) + '</tr>'

#display column heading text, links, sort order that allow changing
ORDER_BY_IMG = {'asc': '/ezid/static/images/asc.png', 'desc': '/ezid/static/images/desc.png'}
SORT_OPPOSITE = {'asc': 'desc', 'desc': 'asc'}
SORT_TIP = {'asc': 'Sorting in ascending order. Click to change to descending order.',
            'desc': 'Sorgint in descending order. Click to change to ascending order.'}
def column_head(request, field, fields_mapped, order_by, sort):
  #if current fields is being ordered by then should show icon, also clicking link or icon will switch order
  if field == order_by:
    overriding_params = {'order_by': field, 'sort': SORT_OPPOSITE[sort] }
  else:
    overriding_params = {'order_by': field, 'sort': sort }
  combined_params = dict(request, **overriding_params)
  url = reverse('ui_manage.index') + "?" + urllib.urlencode(combined_params)
  if field == order_by:
    sort_icon = "<a href='" + url + "' title='" + SORT_TIP[sort] + "'>" + \
        "<img src='" + ORDER_BY_IMG[sort] + "' alt='" + SORT_TIP[sort] + "'></a>&nbsp;&nbsp;"
  else:
    sort_icon = ''
  column_link = "<a href='" + url + "' title='Sort on this column'>" + escape(fields_mapped[field]) + "</a>"
  return sort_icon + column_link
          
@register.simple_tag
def data_row(record, fields_selected, field_display_types):
  return '<td>' + '</td><td>'.join([ formatted_field(record, f, field_display_types) for f in fields_selected]) + '</td>'

@register.simple_tag
def latest_modification_string(dictionary):
  """returns string of latest modification whether it's created or modified date"""
  if dictionary['createTime'] + 2 < dictionary['updateTime']:
    return "modified " + escape(datetime.datetime.fromtimestamp(dictionary['updateTime']).strftime("%m/%d/%Y %I:%M:%S %p"))
  else:
    return "created " + escape(datetime.datetime.fromtimestamp(dictionary['updateTime']).strftime("%m/%d/%Y %I:%M:%S %p"))

FUNCTIONS_FOR_FORMATTING = { \
  'string'         : lambda x: string_value(x), \
  'identifier'     : lambda x: "<a href='" + reverse('ui_manage.details', args=[x]) + "'>" + escape(x) + "</a>", \
  'datetime'       : lambda x: escape(datetime.datetime.fromtimestamp(x).strftime("%m/%d/%Y %I:%M %p")), \
  'owner_lookup'   : lambda x: cached_id_lookup(x) }

def formatted_field(record, field_name, field_display_types):
  value = record[field_name]
  formatting = field_display_types[field_name]
  return FUNCTIONS_FOR_FORMATTING[formatting](value)

def string_value(x):
  if x is None:
    return ''
  else:
    return escape(x)

cached_users = {}
def cached_id_lookup(x):
  if not x in cached_users:
    try:
      cached_users[x] = idmap.getAgent(x)[0]
    except:
      return 'unknown'
  return escape(cached_users[x])
  

def percent_width(item_weight, total):
  return str(int(round(item_weight/total*1000))/10.0) + '%'

def chunks(l, n):
    return [l[i:i+n] for i in range(0, len(l), n)]
  
@register.simple_tag
def pager_display(request, current_page, total_pages, page_size):
  if total_pages < 2: return ''
  #half_to_first = (current_page - 1) / 2
  #half_to_last = (total_pages - current_page) / 2 + current_page
  temp_p = list(set(itertools.chain([1, 2, 3], \
                                   #[half_to_first - 1, half_to_first, half_to_first + 1], \
                                   #[half_to_last - 1, half_to_last, half_to_last + 1], \
                                   [current_page -1, current_page, current_page + 1], \
                                   [total_pages - 2, total_pages - 1, total_pages])))
  disp_pages = sorted([x for x in temp_p if x>0 and x <= total_pages])
  p_out = ''
  last_p = 0
  if current_page > 1:
    p_out += page_link(request, current_page, current_page - 1, "< prev", page_size) + ' '
  for p in disp_pages:
    if last_p < p - 1:
      p_out += '... '
    p_out += page_link(request, current_page, p, str(p), page_size) + ' '
    last_p = p
  if current_page < total_pages:
    p_out += page_link(request, current_page, current_page + 1, "next >", page_size) + ' '
  return p_out

def page_link(request, current_page, this_page, link_text, page_size):
  combined_params = dict(request, **{'p': this_page, 'ps': page_size})
  url = reverse('ui_manage.index') + "?" + urllib.urlencode(combined_params)
  if current_page == this_page:
    return "<span class='pagercurrent'>" + escape(link_text) + "</span>"
  else:
    return "<a href='" + url + "' class='pagerlink'>" + escape(link_text) + "</a>"