from django import template
from django.core.urlresolvers import reverse
import string

register = template.Library()

MENUS = (
          ("Home", "ui_home.index",
            ( ('Why EZID?', 'ui_home.why', () ),
              ('Understanding Identifiers', 'ui_home.understanding', () ),
              ('Pricing', 'ui_home.pricing', () ),
              ('Documentation', 'ui_home.documentation', () ),
              ('Outreach', 'ui_home.outreach', () ),
              ('Community', 'ui_home.community', () )
            ) 
          ),
          ("Manage_IDs", 'ui_manage.index', ()),
          ("Create IDs", 'ui_create.index',
            ( ("Simple", 'ui_create.simple', ()),
              ("Advanced", "ui_create.advanced", ())
            )
          ),
          ("Lookup ID", 'ui_lookup.index', ()),
          ("Demo", 'ui_demo.index',
            ( ("Simple", 'ui_demo.simple', ()),
              ("Advanced", "ui_demo.advanced", ())
            )
          ),
          ("Admin", 'ui_admin.index',
            ( ("View usage", 'ui_admin.usage', ()),
              ("Manage user accounts", 'ui_admin.manage_users', ()),
              ("Manage groups", 'ui_admin.manage_groups', ()),
              ("System status", 'ui_admin.system_status', ()),
              ("Create alert message", 'ui_admin.alert_message', ())
            )
          )
        )

@register.simple_tag
def top_menu(current_func):
  acc = ''
  for menu in MENUS:
    acc += top_menu_item(menu,
      string.split(current_func, '.')[0] == string.split(menu[1], '.')[0])
  return acc
  
@register.simple_tag
def secondary_menu(current_func):
  matched = False
  for menu in MENUS:
    if string.split(current_func,'.')[0] == string.split(menu[1], '.')[0]:
      matched = True
      break
  if not matched or not menu[2]: return ''
  acc = []
  for m in menu[2]:
    acc.append(display_item(m,
                string.split(current_func, '.')[1] == string.split(m[1], '.')[1]))
  return '&nbsp;&nbsp;|&nbsp;&nbsp;'.join(acc)
  
  

def top_menu_item(tup, is_current):
  return "<div>" + display_item(tup, is_current) + "</div>"


def display_item(tup, is_current):
  u = reverse(tup[1])
  if is_current:
    if not tup[2]:
      return """<span class="menu_current">""" + tup[0] + """</span>"""
    else:
      return """<a href="%(path)s" class="menu_current">%(text)s</a>""" % {'path':u, 'text':tup[0] }
  else:
    return """<a href="%(path)s">%(text)s</a>""" % {'path':u, 'text':tup[0] }