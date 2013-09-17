from django import template
from django.core.urlresolvers import reverse
from django.utils.html import escape
import string
import config

register = template.Library()

#this sets the menu and submenu structure along with information about its link
#and also allows matching with current items for different display
#structure: name, function, menu role, submenus

#the roles are now proliferating, so the documentation is:
# 'public' -- anyone can click the menu item for this
# 'user' -- only logged in users can click the item, but it is still displayed as unlinked/grayed-out
# 'admin' -- only EZID administrative users will have these menus displayed
# 'group_admin' -- only group administrative users will have these menu displayed
# 'realm_admin' -- only realm administrators will have these menus displayed
# if a user has more than one administrative role, they will see the one most permission

MENUS = (
          ("Home", "ui_home.index", 'public',
            ( ('Why EZID?', 'ui_home.why', 'public', () ),
              ('Understanding Identifiers', 'ui_home.understanding', 'public', () ),
              ('Pricing', 'ui_home.pricing', 'public', () ),
              ('Documentation', 'ui_home.documentation', 'public', () ),
              ('Outreach', 'ui_home.outreach', 'public', () ),
              ("Who's using EZID?", 'ui_home.community', 'public', () )
            ) 
          ),
          ("Manage IDs", 'ui_manage.index', 'user', ()),
          ("Create IDs", 'ui_create.index', 'user',
            ( ("Simple", 'ui_create.simple', 'user', ()),
              ("Advanced", "ui_create.advanced", 'user', ())
            )
          ),
          ("Lookup ID", 'ui_lookup.index', 'public', ()),
          ("Demo", 'ui_demo.index', 'public',
            ( ("Simple", 'ui_demo.simple', 'public', ()),
              ("Advanced", "ui_demo.advanced", 'public', ())
            )
          ),
          ("Admin", 'ui_admin.index', 'admin',
            ( ("Usage", 'ui_admin.usage', 'admin', ()),
              ("Users", 'ui_admin.manage_users', 'admin', ()),
              ("Groups", 'ui_admin.manage_groups', 'admin', ()),
              ("Status", 'ui_admin.system_status', 'admin', ()),
              ("Alerts", 'ui_admin.alert_message', 'admin', ()),
              ("New account", 'ui_admin.new_account', 'admin', ())
            )
          )
        )

@register.simple_tag
def top_menu(current_func, session):
  items = [ "<div>" + display_item(menu, session, string.split(current_func, '.')[0] == string.split(menu[1], '.')[0]) + "</div>" \
           for menu in MENUS]
  items = [x for x in items if x != "<div></div>"]
  return "".join(items)
  
@register.simple_tag
def secondary_menu(current_func, session):
  matched = False
  #get the appropriate submenu
  for menu in MENUS:
    if string.split(current_func,'.')[0] == string.split(menu[1], '.')[0]:
      matched = True
      break
  if not matched or not menu[3]: return ''
  acc = []
  for m in menu[3]:
    acc.append(display_item(m, session,
                string.split(current_func, '.')[1] == string.split(m[1], '.')[1]))
  return '<span class="pad">|</span>'.join(acc)
  
  
#no longer used
#def top_menu_item(tup, session, is_current):
#  return "<div>" + display_item(tup, session, is_current) + "</div>"


def display_item(tup, session, is_current):
  u = reverse(tup[1])
  if is_current:
    if tup[2] == 'public' or (tup[2] == 'user' and session.has_key('auth')): # if this is public always display it
      return """<a href="%(path)s" class="menu_current">%(text)s</a>""" % {'path':u, 'text':tup[0] }
    else: # don't display as a link if this is current menu and not public and not authenticated
      return """<span class="menu_current">""" + tup[0] + """</span>"""
  else:
    if tup[2] == 'public' or (tup[2] == 'user' and session.has_key('auth')): #display linked if public link or user link and authorized
      return """<a href="%(path)s">%(text)s</a>""" % {'path':u, 'text':tup[0] }
    elif tup[2] == 'user': #display user links as grayed out when not logged in
      return """<span class="menu_disabled">""" + tup[0] + """</span>"""
    elif session.has_key('auth') and admin_level(session) == tup[2]:
      return """<a href="%(path)s">%(text)s</a>""" % {'path':u, 'text':tup[0] }
    else:
      return ''
    
def admin_level(session):
  """get the level of admin for the current user. if mulitple levels of admin
  return the highest"""
  # 'admin' -- only EZID administrative users will have these menus displayed
  # 'group_admin' -- only group administrative users will have these menu displayed
  # 'realm_admin' -- only realm administrators will have these menus displayed
  if config.config("ldap.admin_username") == session['auth'].user[0]: # EZID admin
    return 'admin'
  elif False == True: #some random undefined test for realm admin
    return 'realm_admin'
  elif False == True: #some random undefined test for group admin
    return 'group_admin'
  
  