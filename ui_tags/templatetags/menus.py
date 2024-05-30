#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import django.urls.resolvers
import django.template
from django.utils.translation import gettext as _

register = django.template.Library()

# This sets the menu and submenu structure for items that need to indicate they are active
# in the top navigation area; And includes link information
# and also allows matching with current items for different display
#  structure: name, function, menu role, submenus
# Demo page and api doc do not have anything active in top nav section (MENU_PUBLIC)

# Nav that shows up for logged in users
MENU_USER = (
    (_("DASHBOARD"), 'ui_admin.dashboard', 'admin', ()),
    (_("MANAGE IDS"), 'ui_manage.index', 'user', ()),
    (
        _("CREATE ID"),
        'ui_create.index',
        'user',
        (
            (_("Simple"), 'ui_create.simple', 'user', ()),
            (_("Advanced"), "ui_create.advanced", 'user', ()),
        ),
    ),
    (_("ACCOUNT SETTINGS"), 'ui_account.edit', 'user', ()),
)

# Tertiary nav
MENU_DEMO = (
    (_("Simple"), 'ui_demo.simple', 'public', ()),
    (_("Advanced"), "ui_demo.advanced", 'public', ()),
)

# Dynamically created menu for subnav; Only displays for logged in users
@register.simple_tag
def menu_user(current_func, session):
    acc = ''
    for i, menu in enumerate(MENU_USER):
        acc += menu_user_item(
            menu,
            session,
            str.split(current_func, '.')[0] == str.split(menu[1], '.')[0],
        )
    return acc


def menu_user_item(tup, _session, is_current):
    u = django.urls.reverse(tup[1])
    # TODO: Check if quotes must be escaped
    acc = f'<a href="{u}" '
    if is_current:
        class_name = 'login-menu__link--selected'
    else:
        class_name = "login-menu__link"
    acc += f'class="{class_name}">{tup[0]}</a>'
    return acc


@register.simple_tag
def learn_breadcrumb(view_title, parent_dir_title=None, parent_dir_link=None):
    home = _("Home")
    learn = _("Learn")
    codeblock = (
        '<div class="general__form"><ul class="breadcrumb">'
        + '<li><a href="/">'
        + str(home)
        + '</a></li>'
        + '<li><a href="/learn">'
        + str(learn)
        + '</a></li>'
    )
    if parent_dir_title is not None:
        if parent_dir_link is None:
            parent_dir_link = ''
        parent_dir_title_tr = _(parent_dir_title)
        codeblock += (
            '<li><a href="/learn/'
            + str(parent_dir_link)
            + '">'
            + str(parent_dir_title_tr)
            + '</a></li>'
        )
    codeblock += '<li class="active">' + str(view_title) + '</li></ul></div>'
    return codeblock


# Simply determines whether an element should be tagged as active; Only used for topmost nav
@register.simple_tag
def active(current_func, view_name):
    if str.split(current_func, '.')[1] == view_name:
        return 'active'
    elif str.split(str.split(current_func, '.')[0], '_')[1] == view_name:
        return 'active'
    return ''
