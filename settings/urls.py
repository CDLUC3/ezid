import django.conf
import django.conf.urls.defaults

def _p (urlPattern, function, kwargs=None):
  # If we're running under Apache, the site is already rooted under
  # "/ezid/" and that prefix doesn't get mentioned here.  But if we're
  # running locally (i.e., sans Apache), then it must be added.
  # (There's probably a better way to do this.)
  if django.conf.settings.DEPLOYMENT_LEVEL == "localdev":
    t = ("^ezid/" + urlPattern, function)
  else:
    t = ("^" + urlPattern, function)
  if kwargs != None: t += (kwargs,)
  return t

urlpatterns = django.conf.urls.defaults.patterns("",
  _p("$", "ui.home"),
  _p("admin$", "ui.admin"),
  _p("admin/reload$", "api.reload"),
  _p("clearhistory$", "ui.clearHistory"),
  _p("create$", "ui.create"),
  _p("help", "ui.help"),
  _p("id/", "dispatch.d", { "function": "identifierDispatcher" }),
  _p("login$", "dispatch.d", { "function": "login" }),
  _p("logout$", "dispatch.d", { "function": "logout" }),
  _p("manage$", "ui.manage"),
  _p("prefix/", "api.mintIdentifier"),
  _p("status$", "api.getStatus")
)

if django.conf.settings.DEPLOYMENT_LEVEL == "localdev":
  urlpatterns += django.conf.urls.defaults.patterns("",
    ("^ezid/static/(?P<path>.*)$", "django.views.static.serve",
    { "document_root": django.conf.settings.MEDIA_ROOT }))

handler404 = "django.views.defaults.page_not_found"
handler500 = "django.views.defaults.server_error"
