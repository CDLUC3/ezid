from django import template
from django.conf import settings
from django.utils.html import escape
from decorators import basictag
import datetime
import urllib
from django.core.urlresolvers import reverse
import idmap
import itertools
from django.utils.translation import ugettext as _

register = template.Library()

@register.simple_tag 
def column_choices(field_order, fields_mapped, fields_selected):
  """this only works when the following context variables are set from the django view:
  field_order is the ordered list of the fields
  fields_mapped is mapping of fields to texual names (second item in list of mapped objects)
  fields_selected is ordered list of selected fields"""
  return "<div class='col-sm-4'>" + "</div><div class='col-sm-4'>".join(\
         [make_check_tag(f, fields_mapped, fields_selected) for f in field_order])\
         + '</div>'

def make_check_tag(item, friendly_names, selected):
  if item in selected:
    checked_str = " checked='checked' "
  else:
    checked_str = ""
  return "<input type='checkbox' id='" + escape(item) + "' name='" + escape(item) + "' value='t'" + checked_str + " \> " \
       + "<label for='" + escape(item) + "'>" + escape(friendly_names[item][1]) + "</label>"

@register.simple_tag 
def column_choices_hidden(fields_selected):
  """Include column choices in request query as hidden fields"""
  hidden = ''
  for f in fields_selected:
    hidden += "<input type='hidden' name='" + f + "' value='t'/>"
  return hidden

@register.simple_tag   
def rewrite_hidden(request, exclude=None):
  hidden = ''
  for key, value in request.iteritems():
    if exclude is None or not (key in exclude):
      hidden += "<input type='hidden' name='" + escape(key) + "' value='" + escape(value) + "'/>"
  return hidden

@register.simple_tag   
def rewrite_hidden_except(request, x):
  return rewrite_hidden(request, [x])

@register.simple_tag   
def rewrite_hidden_nocols(request, field_order):
  exclude = field_order + ['submit_checks']
  return rewrite_hidden(request, exclude)

@register.simple_tag
def header_row(request, fields_selected, fields_mapped, order_by, sort, primary_page):
  r = "<thead><tr>" + ''.join([column_head(request, x, fields_mapped, order_by, sort, \
      primary_page) for x in fields_selected]) + '</tr></thead>'
  return r

#display column heading text, links, sort order that allow changing
ORDER_BY_CLASS = {'asc': 'sort_asc', 'desc': 'sort_desc'}
SORT_OPPOSITE = {'asc': 'desc', 'desc': 'asc'}
SORT_TIP = {'asc': 'Sorting in ascending order. Click to change to descending order.',
            'desc': 'Sorting in descending order. Click to change to ascending order.'}
def column_head(request, field, fields_mapped, order_by, sort, primary_page):
  #if current fields is being ordered by then should show icon, also clicking link or icon will switch order
  if field == order_by:
    overriding_params = {'order_by': field, 'sort': SORT_OPPOSITE[sort] }
  else:
    overriding_params = {'order_by': field, 'sort': sort }
  combined_params = dict(request.dict(), **overriding_params)
  # If sorting, set result to first page
  if 'p' in combined_params: combined_params['p'] = 1
  url = reverse(primary_page) + "?" + urllib.urlencode(combined_params)
  r = "<th "
  if field == order_by:
    r += "class='" + ORDER_BY_CLASS[sort] + "'><a title='" + SORT_TIP[sort] + "' "
    # "<div class='order_by_col'><a href='" + url + "' title='" + SORT_TIP[sort] + "'>" + \
    #   "<img src='" + ORDER_BY_IMG[sort] + "' alt='" + SORT_TIP[sort] + "'></a></div>"
  else:
    r += "class='sorting'><a title='Sort on this column' "
  # column_link = "<a href='" + url + "' title='Sort on this column'>" + escape(fields_mapped[field][1]) + "</a>"
  r += "class='table__th-link' href='" + url + "'>" + escape(fields_mapped[field][1]) + "</a></th>"
  return r 

#need to pass in account co owners because it's obnoxiously used in the co-owners field and is added
#to database values instead of being a purer value 
@register.simple_tag
def data_row(record, fields_selected, field_display_types, account_co_owners, testPrefixes):
  assert 'c_identifier' in record
  id_href_tag_head = "<a href='/id/" + record['c_identifier'] + "'>" 
  return '<td>' + '</td><td>'.join([ formatted_field(record, f, field_display_types, \
    account_co_owners, testPrefixes, id_href_tag_head) for f in fields_selected]) + '</td>'

FUNCTIONS_FOR_FORMATTING = {
  'string'         : lambda x, coown, tp, href: string_value(x, href),
  'identifier'     : lambda x, coown, tp, href: identifier_disp(x, tp),
  'datetime'       : lambda x, coown, tp, href: datetime_disp(x, href), 
  'owner_lookup'   : lambda x, coown, tp, href: id_lookup(x),
  'coowners'       : lambda x, coown, tp, href: co_owner_disp(x, coown)
}

def formatted_field(
  record, field_name, field_display_types, account_co_owners, testPrefixes, href):
    value = record[field_name]
    formatting = field_display_types[field_name]
    return FUNCTIONS_FOR_FORMATTING[formatting](value, account_co_owners, testPrefixes, href)

def string_value(x, href):
  if x is None or x.strip() == '':
    return '&nbsp;'
  else:
    return href + escape(x) + "</a>"

@register.simple_tag  
def identifier_disp(x, testPrefixes):
  for pre in testPrefixes:
    if x.startswith(pre['prefix']):
      return "<a href='/id/" + x + "' class='fakeid'>" + escape(x) + "</a>"
  return "<a href='/id/" + x + "'>" + escape(x) + "</a>"
  
def datetime_disp(x, href):
  return href +\
    escape(datetime.datetime.utcfromtimestamp(x).strftime(settings.TIME_FORMAT_UI_METADATA)) +\
    " UTC</a>"

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

@register.simple_tag
def pager_display(request, current_page, total_pages, page_size, select_position):
  if total_pages < 2: return ''
  p_out = ''
  s_total = str(total_pages)
  empty = ''
  if current_page > 1:
    p_out += page_link(request, 1, empty, page_size, 'pagination__first', \
      _("First page of results")) + ' '
    p_out += page_link(request, current_page - 1, _("Previous"), page_size,\
      'pagination__prev', _("Previous page of results")) + ' '
  p_out += "<input id='page-directselect-" + select_position + \
           "' type='number' class='pagination__input' min='1' " + \
           "max='"  + s_total  + "' name='p' value='" + str(current_page) + "'/> " + \
           _("of") + " " + s_total + " "
  if current_page < total_pages:
    p_out += page_link(request, current_page + 1, _("Next"), page_size, \
      'pagination__next', _("Next page of results")) + ' '
    p_out += page_link(request, total_pages, empty, page_size, \
      'pagination__last', _("Last page of results")) + ' '
  return p_out

def page_link(request, this_page, link_text, page_size, cname, title=None):
  attr_aria = " aria-label='" + title + "'" if title else ""
  return "<button data-page='" + str(this_page) + "' class='" + cname + "'" + \
    attr_aria + ">" + escape(link_text) + "</button>"
