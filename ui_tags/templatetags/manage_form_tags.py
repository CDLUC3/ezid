from django import template
from django.conf import settings
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
ORDER_BY_IMG = {'asc': '/static/images/tri_up.png', 'desc': '/static/images/tri_down.png'}
SORT_OPPOSITE = {'asc': 'desc', 'desc': 'asc'}
SORT_TIP = {'asc': 'Sorting in ascending order. Click to change to descending order.',
            'desc': 'Sorting in descending order. Click to change to ascending order.'}
def column_head(request, field, fields_mapped, order_by, sort):
  #if current fields is being ordered by then should show icon, also clicking link or icon will switch order
  if field == order_by:
    overriding_params = {'order_by': field, 'sort': SORT_OPPOSITE[sort] }
  else:
    overriding_params = {'order_by': field, 'sort': sort }
  combined_params = dict(request, **overriding_params)
  url = reverse('ui_manage.index') + "?" + urllib.urlencode(combined_params)
  if field == order_by:
    sort_icon = "<div class='order_by_col'><a href='" + url + "' title='" + SORT_TIP[sort] + "'>" + \
        "<img src='" + ORDER_BY_IMG[sort] + "' alt='" + SORT_TIP[sort] + "'></a></div>"
  else:
    sort_icon = ''
  column_link = "<a href='" + url + "' title='Sort on this column'>" + escape(fields_mapped[field]) + "</a>"
  return sort_icon + column_link

#need to pass in account co owners because it's obnoxiously used in the co-owners field and is added
#to database values instead of being a purer value 
@register.simple_tag
def data_row(record, fields_selected, field_display_types, account_co_owners, testPrefixes):
  return '<td>' + '</td><td>'.join([ formatted_field(record, f, field_display_types, account_co_owners, testPrefixes) \
               for f in fields_selected]) + '</td>'

FUNCTIONS_FOR_FORMATTING = { \
  'string'         : lambda x, coown, tp: string_value(x), \
  'identifier'     : lambda x, coown, tp: identifier_disp(x, tp), \
  'datetime'       : lambda x, coown, tp: escape(datetime.datetime.fromtimestamp(x).strftime(settings.TIME_FORMAT_UI_METADATA)), \
  'owner_lookup'   : lambda x, coown, tp: id_lookup(x), \
  'coowners'       : lambda x, coown, tp: co_owner_disp(x, coown) }

def formatted_field(record, field_name, field_display_types, account_co_owners, testPrefixes):
  value = record[field_name]
  formatting = field_display_types[field_name]
  return FUNCTIONS_FOR_FORMATTING[formatting](value, account_co_owners, testPrefixes)

def string_value(x):
  if x is None:
    return ''
  else:
    return escape(x)

@register.simple_tag  
def identifier_disp(x, testPrefixes):
  for pre in testPrefixes:
    if x.startswith(pre['prefix']):
      return "<a href='/id/" + x + "' class='fakeid'>" + escape(x) + "</a>"
  return "<a href='/id/" + x + "'>" + escape(x) + "</a>"
  
  
def co_owner_disp(x, coown):
  str_x = ''
  if not x is None:
    str_x = x
  if str_x != '' and coown != '':
    return escape(str_x) + "," + "<span class='account_co_owners'>" + escape(coown) + "</span>"
  else:
    return escape(str_x) + "<span class='small_co_owners'>" + escape(coown) + "</span>"

def id_lookup(x):
  try:
    return escape(idmap.getAgent(x)[0])
  except:
    return 'unknown'
  

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
