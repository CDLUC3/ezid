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
  if ',' not in x:
    vals = [x]
  else:
    vals = x.split(",")
  return rewrite_hidden(request, vals)

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
ORDER_BY_CLASS = {'asc': 'sort__asc', 'desc': 'sort__desc'}
SORT_OPPOSITE = {'asc': 'desc', 'desc': 'asc'}
SORT_TIP = {'asc': 'Sorting in ascending order. Click to change to descending order.',
            'desc': 'Sorting in descending order. Click to change to ascending order.'}
def column_head(request, field, fields_mapped, order_by, sort, primary_page):
  c = request.copy()
  c['order_by'] = field
  #if current fields is being ordered by then should show icon, also clicking link or icon will switch order
  if field == order_by:
    c['sort'] = SORT_OPPOSITE[sort]
  else:
    c['sort'] = sort
  # If sorting, set result to first page
  if 'p' in c: c['p'] = 1
  form_and_hidden = "<form method='get' action='" + reverse(primary_page) +\
    "' role='form'>" + rewrite_hidden(c)
  r = "<th>" + escape(fields_mapped[field][1]) + form_and_hidden
  if field == order_by:
    r += "<button class='" + ORDER_BY_CLASS[sort] + "' aria-label='" + SORT_TIP[sort] + "'>"
  else:
    r += "<button class='sorting' aria-label='Sort on this column'>"
  r += "</button></form></th>"
  return r 

#need to pass in account co owners because it's obnoxiously used in the co-owners field and is added
#to database values instead of being a purer value 
@register.simple_tag
def data_row(record, fields_selected, field_display_types, testPrefixes):
  assert 'c_identifier' in record
  id_href_tag_head = "<a href='/id/" + record['c_identifier'] + "' class='link__primary'>" 
  return '<td>' + '</td><td>'.join([ formatted_field(record, f, field_display_types, \
    testPrefixes, id_href_tag_head) for f in fields_selected]) + '</td>'

FUNCTIONS_FOR_FORMATTING = {
  'datetime'       : lambda x, tp, href: datetime_disp(x, href), 
  'identifier'     : lambda x, tp, href: identifier_disp(x, tp),
  'string'         : lambda x, tp, href: string_value(x, href),
}

def formatted_field(
  record, field_name, field_display_types, testPrefixes, href):
    value = record[field_name]
    formatting = field_display_types[field_name]
    return FUNCTIONS_FOR_FORMATTING[formatting](value, testPrefixes, href)

def string_value(x, href):
  if x is None or x.strip() == '':
    return '&nbsp;'
  else:
    return href + escape(x) + "</a>"

@register.simple_tag  
def identifier_disp(x, testPrefixes):
  for pre in testPrefixes:
    if x.startswith(pre['prefix']):
      return "<a href='/id/" + x + "' class='link__primary fakeid'>" + escape(x) + "</a>"
  return "<a href='/id/" + x + "' class='link__primary'>" + escape(x) + "</a>"
  
def datetime_disp(x, href):
  return href +\
    escape(datetime.datetime.utcfromtimestamp(x).strftime(settings.TIME_FORMAT_UI_METADATA)) +\
    " UTC</a>"

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
    attr_aria + " type='button'>" + escape(link_text) + "</button>"
