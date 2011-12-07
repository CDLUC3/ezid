import django.conf
import django.conf.urls.defaults

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
  _p("$", "ui_home.index"),
  _p("home/why$", "ui_home.why"),
  _p("home/understanding$", "ui_home.understanding"),
  _p("home/pricing$", "ui_home.pricing"),
  _p("home/documentation$", "ui_home.documentation"),
  _p("home/outreach$", "ui_home.outreach"),
  _p("home/community$", "ui_home.community"),
  _p("manage$", "ui_manage.index"),
  _p("create$", "ui_create.index"),
  _p("create/simple$", "ui_create.simple"),
  _p("create/advanced$", "ui_create.advanced"),
  _p("lookup$", "ui_lookup.index"),
  _p("demo$", "ui_demo.index"),
  _p("demo/simple$", "ui_demo.simple"),
  _p("demo/advanced$", "ui_demo.advanced"),
  _p("admin$", "ui_admin.index"),
  _p("admin/usage$", "ui_admin.usage"),
  _p("admin/manage_users$", "ui_admin.manage_users"),
  _p("admin/manage_groups$", "ui_admin.manage_groups"),
  _p("admin/system_status$", "ui_admin.system_status"),
  _p("admin/alert_message$", "ui_admin.alert_message"),
  _p("account/edit$", "ui_account.edit"),
  _p("account/login$", "ui_account.login"),
  _p("account/logout$", "ui_account.logout"),
  _p("info/about_us$", "ui_info.about_us"),
  _p("info/help$", "ui_info.help"),
  _p("info/contact_us$", "ui_info.contact_us"),
  _p("info/privacy$", "ui_info.privacy"),
)

if django.conf.settings.STANDALONE:
  urlpatterns += django.conf.urls.defaults.patterns("",
    ("^ezid/static/(?P<path>.*)$", "django.views.static.serve",
    { "document_root": django.conf.settings.MEDIA_ROOT }))

handler404 = "django.views.defaults.page_not_found"
handler500 = "django.views.defaults.server_error"
