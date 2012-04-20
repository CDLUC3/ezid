from django import template
from django.core.urlresolvers import reverse
from django.utils.html import escape
import string
import config

register = template.Library()

#this sets the menu and submenu structure along with information about its link
#and also allows matching with current items for different display
# structure: name, function, menu role, submenus

MENUS = (
          ("Home", "ui_home.index", 'public',
            ( ('Why EZID?', 'ui_home.why', 'public', () ),
              ('Understanding Identifiers', 'ui_home.understanding', 'public', () ),
              ('Pricing', 'ui_home.pricing', 'public', () ),
              ('Documentation', 'ui_home.documentation', 'public', () ),
              ('Outreach', 'ui_home.outreach', 'public', () ),
              ('Community', 'ui_home.community', 'public', () )
            ) 
          ),
          ("Manage IDs", 'ui_manage.index', 'user', ()),
          ("Create IDs", 'ui_create.index', 'user',
            ( ("Simple", 'ui_create.simple', 'user', ()),
              ("Advanced", "ui_create.advanced", 'user', ())
            )
          ),
          ("Lookup ID", 'ui_lookup.index', 'public', ()),
          ("Test", 'ui_demo.index', 'public',
            ( ("Simple", 'ui_demo.simple', 'public', ()),
              ("Advanced", "ui_demo.advanced", 'public', ())
            )
          ),
          ("Admin", 'ui_admin.index', 'admin',
            ( ("View usage", 'ui_admin.usage', 'admin', ()),
              ("Manage user accounts", 'ui_admin.manage_users', 'admin', ()),
              ("Manage groups", 'ui_admin.manage_groups', 'admin', ()),
              ("System status", 'ui_admin.system_status', 'admin', ()),
              ("Create alert message", 'ui_admin.alert_message', 'admin', ())
            )
          )
        )

@register.simple_tag
def top_menu(current_func, session):
  #print type(session['auth']).__name__
  #print session.keys()
  acc = ''
  for menu in MENUS:
    acc += top_menu_item(menu, session,
      string.split(current_func, '.')[0] == string.split(menu[1], '.')[0])
  return acc
  
@register.simple_tag
def secondary_menu(current_func, session):
  matched = False
  for menu in MENUS:
    if string.split(current_func,'.')[0] == string.split(menu[1], '.')[0]:
      matched = True
      break
  if not matched or not menu[3]: return ''
  acc = []
  for m in menu[3]:
    acc.append(display_item(m, session,
                string.split(current_func, '.')[1] == string.split(m[1], '.')[1]))
  return '&nbsp;&nbsp;|&nbsp;&nbsp;'.join(acc)
  
  

def top_menu_item(tup, session, is_current):
  return "<div>" + display_item(tup, session, is_current) + "</div>"


def display_item(tup, session, is_current):
  u = reverse(tup[1])
  if is_current:
    if not tup[3]:
      #return """<span class="menu_current">""" + tup[0] + """</span>"""
      return """<a href="%(path)s" class="menu_current">%(text)s</a>""" % {'path':u, 'text':tup[0] }
    else:
      return """<a href="%(path)s" class="menu_current">%(text)s</a>""" % {'path':u, 'text':tup[0] }
  else:
    if tup[2] == 'public' or (tup[2] == 'user' and session.has_key('auth')):
      return """<a href="%(path)s">%(text)s</a>""" % {'path':u, 'text':tup[0] }
    elif tup[2] == 'user':
      return """<span class="menu_disabled">""" + tup[0] + """</span>"""
    elif tup[2] == 'admin' and session.has_key('auth') and config.config("ldap.admin_username") == session['auth'].user[0]:
      return """<a href="%(path)s">%(text)s</a>""" % {'path':u, 'text':tup[0] }
    else:
      return ''