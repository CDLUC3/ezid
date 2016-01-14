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
  for i, menu in enumerate(MENU_USER):
    acc += menu_user_item(menu, session,
      string.split(current_func, '.')[0] == string.split(menu[1], '.')[0])
  return acc

def menu_user_item(tup, session, is_current):
  u = reverse(tup[1])
  acc = '<a href=\"%s\" ' % u
  if is_current:
    class_name = "login-menu__link--selected"
  else:
    class_name = "login-menu__link"
  acc += 'class=\"' + class_name + '\">%s</a>' % tup[0]
  return acc

@register.simple_tag
def learn_breadcrumb(view_title, parent_dir_title=None, parent_dir_link=None):
  home = _("Home")
  learn = _("Learn")
  codeblock = '<div class="container"><ul class="breadcrumb">' + \
    '<li><a href="/">' + unicode(home) + '</a></li>' + \
    '<li><a href="/learn">' + unicode(learn) + '</a></li>'
  if parent_dir_title is not None:
    if parent_dir_link is None: 
      parent_dir_link = ''
    parent_dir_title_tr = _(parent_dir_title)
    codeblock += '<li><a href="/learn/' + unicode(parent_dir_link) + '">' + \
      unicode(parent_dir_title_tr) + '</a></li>' 
  codeblock += '<li class="active">' + unicode(view_title) + '</li></ul></div>' 
  return codeblock

# Simply determines whether an element should be tagged as active; Only used for topmost nav
@register.simple_tag
def active(current_func, view_name):
  if string.split(current_func, '.')[1] == view_name:
    return 'active'
  elif string.split(string.split(current_func, '.')[0], '_')[1] == view_name:
    return 'active'
  return ''
