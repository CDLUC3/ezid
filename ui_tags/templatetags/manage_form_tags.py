from django import template
#from django.conf import settings
from django.utils.html import escape
from decorators import basictag
#from django.core.urlresolvers import reverse
#import pdb
import datetime

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
def header_row(fields_selected, fields_mapped, field_widths):
  total_width = 0
  for item in fields_selected:
    total_width += field_widths[item]
  return '<tr>' + ''.join([("<th style='width:" + percent_width(field_widths[x], total_width) + \
                            "'>" + escape(fields_mapped[x]) + "</th>"  ) \
          for x in fields_selected]) + '</tr>'
          
@register.simple_tag
def data_row(record, fields_selected, field_display_types):
  return '<td>' + ''.join([ formatted_field(record, f, field_display_types) for f in fields_selected]) + '</td>'

@register.simple_tag
def latest_modification_string(dictionary):
  """returns string of latest modification whether it's created or modified date"""
  if dictionary['createTime'] + 2 < dictionary['updateTime']:
    return "modified " + escape(datetime.datetime.fromtimestamp(dictionary['updateTime']))
  else:
    return "created " + escape(datetime.datetime.fromtimestamp(dictionary['updateTime']))

def formatted_field(record, field_name, field_display_types):
  pass

def percent_width(item_weight, total):
  return str(int(round(item_weight/total*1000))/10.0) + '%'

def chunks(l, n):
    return [l[i:i+n] for i in range(0, len(l), n)]

  