from django import template
from django.core.urlresolvers import reverse
import string
import config

register = template.Library()

# This sets the menu and submenu structure for items that need to indicate they are active
# in the top navigation area; And includes link information
# and also allows matching with current items for different display
#  structure: name, function, menu role, submenus
# Demo page and api doc do not have anything active in top nav section (MENU_PUBLIC)

# Nav that shows up for logged in users
MENU_USER = (
          ("DASHBOARD", 'ui_admin.index', 'admin', ()), #Improved feature
          ("MANAGE IDS", 'ui_manage.index', 'user', ()),
          ("CREATE ID", 'ui_create.index', 'user',
            ( ("Simple", 'ui_create.simple', 'user', ()),
              ("Advanced", "ui_create.advanced", 'user', ())
            )
          ),
          ("ACCOUNT SETTINGS", 'ui_account.edit', 'user', ())
        )

# Tertiary nav
MENU_DEMO = (
             ("Simple", 'ui_demo.simple', 'public', ()),
             ("Advanced", "ui_demo.advanced", 'public', ())
            )

#Dynamically created menu for subnav; Only displays for logged in users
@register.simple_tag
def menu_user(current_func, session):
  #print type(session['auth']).__name__
  #print session.keys()
  acc = ''
  is_last = False 
  for i, menu in enumerate(MENU_USER):
    if i == len(MENU_USER) - 1:
      is_last = True
    acc += menu_user_item(menu, session,
      string.split(current_func, '.')[0] == string.split(menu[1], '.')[0], is_last)
  return acc

def menu_user_item(tup, session, is_current, is_last_menu_item):
  u = reverse(tup[1])
  acc = ''
  if is_current:
    acc += '<li class="active">'
  else:
    acc += '<li>'
  acc += """<a class="not-text" href="%(path)s">%(text)s</a>""" % {'path':u, 'text':tup[0] }
  if not is_last_menu_item:
    # This span creates a divider between list elements
    acc += '<span></span>'
  acc += '</li>'
  return acc

@register.simple_tag
def learn_breadcrumb(view_title):
  codeblock = '<div class="container"><ul class="breadcrumb">' + \
    '<li><a href="/">Home</a></li><li><a href="/learn">Learn</a></li>' + \
    '<li class="active">' + view_title + '</li></ul></div>' 
  return codeblock

# Simply determines whether an element should be tagged as active; Only used for topmost nav
@register.simple_tag
def active(current_func, view_name):
  if string.split(current_func, '.')[1] == view_name:
    return 'active'
  elif string.split(string.split(current_func, '.')[0], '_')[1] == view_name:
    return 'active'
  return ''
