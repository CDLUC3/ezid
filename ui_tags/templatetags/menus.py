from django import template
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
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
          (_("DASHBOARD"), 'ui_admin.index', 'admin', ()), #Improved feature
          (_("MANAGE IDS"), 'ui_manage.index', 'user', ()),
          (_("CREATE ID"), 'ui_create.index', 'user',
            ( (_("Simple"), 'ui_create.simple', 'user', ()),
              (_("Advanced"), "ui_create.advanced", 'user', ())
            )
          ),
          (_("ACCOUNT SETTINGS"), 'ui_account.edit', 'user', ())
        )

# Tertiary nav
MENU_DEMO = (
             (_("Simple"), 'ui_demo.simple', 'public', ()),
             (_("Advanced"), "ui_demo.advanced", 'public', ())
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
  home = _("Home")
  learn = _("Learn")
  documentation = _("Documentation")
  codeblock = '<div class="container"><ul class="breadcrumb">' + \
    '<li><a href="/">' + home + '</a></li><li><a href="/learn">' + learn + '</a></li>' + \
    '<li><a href="/learn/#04">' + documentation + '</a></li>' + \
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
