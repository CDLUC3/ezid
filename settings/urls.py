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

urlpatterns = django.conf.urls.defaults.patterns("",

  # UI - RENDERED FROM TEMPLATES IN INFO REPOSITORY
  _p("/?$", "ui_home.index"),
  _p("home/why$", "ui_home.why"),
  _p("home/understanding$", "ui_home.understanding"),
  _p("home/pricing$", "ui_home.pricing"),
  _p("home/documentation$", "ui_home.documentation"),
  _p("home/outreach$", "ui_home.outreach"),
  _p("home/community$", "ui_home.community"),
  _p("home/(\w+)$", "ui_home.no_menu"),

  # UI - OTHER
  _p("manage/?$", "ui_manage.index"),
  _p("manage/edit/(.*)", "ui_manage.edit"),
  _p("create/?$", "ui_create.index"),
  _p("create/simple$", "ui_create.simple"),
  _p("create/advanced$", "ui_create.advanced"),
  _p("lookup/?$", "ui_lookup.index"),
  _p("demo/?$", "ui_demo.index"),
  _p("demo/simple$", "ui_demo.simple"),
  _p("demo/advanced$", "ui_demo.advanced"),
  _p("admin/?$", "ui_admin.index", { "ssl": True }),
  _p("admin/usage$", "ui_admin.usage", { "ssl": True }),
  _p("admin/manage_users$", "ui_admin.manage_users", { "ssl": True }),
  _p("admin/add_user$", "ui_admin.add_user", { "ssl": True }),
  _p("admin/manage_groups$", "ui_admin.manage_groups", { "ssl": True }),
  _p("admin/add_group$", "ui_admin.add_group", { "ssl": True }),
  _p("admin/system_status$", "ui_admin.system_status", { "ssl": True }),
  _p("admin/ajax_system_status$", "ui_admin.ajax_system_status"),
  _p("admin/alert_message$", "ui_admin.alert_message", { "ssl": True }),
  _p("admin/new_account$", "ui_admin.new_account", { "ssl": True }),
  _p("account/edit$", "ui_account.edit", { "ssl": True }),
  _p("account/pwreset(?P<pwrr>/.*)?$", "ui_account.pwreset", { "ssl": True }),
  _p("ajax_hide_alert$", "ui.ajax_hide_alert"),
  _p("contact$", "ui.contact"),
  _p("doc/[\w.]*\\.(?:html|py)$", "ui.doc"),
  _p("tombstone/id/", "ui.tombstone"),

  # SHARED BETWEEN UI AND API
  _p("id/", "dispatch.d", { "uiFunction": "ui_manage.details",
    "apiFunction": "api.identifierDispatcher" }),
  _p("login$", "dispatch.d", { "uiFunction": "ui_account.login",
    "apiFunction": "api.login", "ssl": True }),
  _p("logout$", "dispatch.d", { "uiFunction": "ui_account.logout",
    "apiFunction": "api.logout" }),

  # API
  _p("shoulder/", "api.mintIdentifier"),
  _p("status$", "api.getStatus"),
  _p("version$", "api.getVersion"),
  _p("admin/reload$", "api.reload")

)

if django.conf.settings.STANDALONE:
  urlpatterns += django.conf.urls.defaults.patterns("",
    ("^ezid/static/(?P<path>.*)$", "django.views.static.serve",
    { "document_root": django.conf.settings.MEDIA_ROOT }))

handler404 = "django.views.defaults.page_not_found"
handler500 = "django.views.defaults.server_error"
