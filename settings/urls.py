import django.conf
import django.conf.urls.defaults
import os
import sys

def _p (urlPattern, function, kwargs=None):
  # If we're running under Apache, the site is already rooted under
  # "/ezid/" and that prefix doesn't get mentioned here.  But if we're
  # running locally (i.e., sans Apache), then it must be added.
  # (There's probably a better way to do this.)
  if django.conf.settings.STANDALONE:
    t = ("^ezid/" + urlPattern, function)
  else:
    t = ("^" + urlPattern, function)
  if kwargs != None: t += (kwargs,)
  return t

# this is commented out
if False:
  urlpatterns = django.conf.urls.defaults.patterns("",
    _p("$", "ui.home"),
    _p("account$", "ui.account", { "ssl": True }),
    _p("admin$", "ui.admin", { "ssl": True }),
    _p("admin/entries$", "ui.getEntries"),
    _p("admin/groups$", "ui.getGroups"),
    _p("admin/reload$", "api.reload"),
    _p("admin/systemstatus$", "ui.systemStatus"),
    _p("admin/users$", "ui.getUsers"),
    _p("clearhistory$", "ui.clearHistory"),
    _p("create$", "ui.create"),
    _p("doc/[\w.]*\\.html$", "ui.doc"),
    _p("help$", "ui.help"),
    _p("id/", "dispatch.d", { "function": "identifierDispatcher" }),
    _p("login$", "dispatch.d", { "function": "login", "ssl": True }),
    _p("logout$", "dispatch.d", { "function": "logout" }),
    _p("manage$", "ui.manage"),
    _p("pwreset(?P<pwrr>/.*)?$", "ui.resetPassword", { "ssl": True }),
    _p("shoulder/", "api.mintIdentifier"),
    _p("status$", "api.getStatus"),
    _p("tombstone/id/", "ui.tombstone")
  )
#end commented out

urlpatterns = django.conf.urls.defaults.patterns("",
  _p("\/?$", "ui_home.index"),
  _p("home/why$", "ui_home.why"),
  _p("home/understanding$", "ui_home.understanding"),
  _p("home/pricing$", "ui_home.pricing"),
  _p("home/documentation$", "ui_home.documentation"),
  _p("home/outreach$", "ui_home.outreach"),
  _p("home/community$", "ui_home.community"),
  _p("home/contact$", "ui_home.contact"),
  _p("home/help$", "ui_home.the_help"),
  _p("home/about_us$", "ui_home.about_us"),
  _p("manage\/?$", "ui_manage.index"),
  _p("id/", "dispatch.d", {"ui_function": "ui_manage.details", "api_function": "api.identifierDispatcher"}),
  _p("manage/edit/(\S+)$", "ui_manage.edit"),
  _p("create\/?$", "ui_create.index"),
  _p("create/simple$", "ui_create.simple"),
  _p("create/advanced$", "ui_create.advanced"),
  _p("lookup\/?$", "ui_lookup.index"),
  _p("demo\/?$", "ui_demo.index"),
  _p("demo/simple$", "ui_demo.simple"),
  _p("demo/advanced$", "ui_demo.advanced"),
  _p("admin\/?$", "ui_admin.index", { "ssl": True }),
  _p("admin/usage$", "ui_admin.usage", { "ssl": True }),
  _p("admin/manage_users$", "ui_admin.manage_users", { "ssl": True }),
  _p("admin/add_user$", "ui_admin.add_user", { "ssl": True }),
  _p("admin/manage_groups$", "ui_admin.manage_groups", { "ssl": True }),
  _p("admin/add_group$", "ui_admin.add_group", { "ssl": True }),
  _p("admin/system_status$", "ui_admin.system_status", { "ssl": True }),
  _p("admin/ajax_system_status$", "ui_admin.ajax_system_status"),
  _p("admin/alert_message$", "ui_admin.alert_message", { "ssl": True }),
  _p("login\/?$", "dispatch.d", { "ui_function": "ui_account.login", "api_function": "api.login", "ssl": True }),
  _p("logout\/?$", "dispatch.d", { "ui_function": "ui_account.logout", "api_function": "api.logout"}),
  _p("account/ajax_hide_alert", "ui_account.ajax_hide_alert"),
  _p("account/edit$", "ui_account.edit", { "ssl": True }),
 # _p("account/logout$", "ui_account.logout"),
  _p("pwreset(?P<pwrr>/.*)?$", "ui_account.pwreset", { "ssl": True })
)

if django.conf.settings.STANDALONE:
  urlpatterns += django.conf.urls.defaults.patterns("",
    ("^ezid/static/(?P<path>.*)$", "django.views.static.serve",
    { "document_root": django.conf.settings.MEDIA_ROOT }))

handler404 = "django.views.defaults.page_not_found"
handler500 = "django.views.defaults.server_error"

#the urls.py seems to load upon the first request for a process
#this seemed to me to be the best place for initializing common
#settings for views that are constant (from Greg's code)
#they are then easily available by uic.varname

#PROJECT_ROOT = os.path.split(os.path.split(os.path.abspath(__file__))[0])[0]
#sys.path.append(os.path.join(PROJECT_ROOT, "code"))
import ui_common as uic
uic.loadConfig()
