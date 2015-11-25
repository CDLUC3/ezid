import django.conf
import django.conf.urls
from django.conf.urls import include

urlpatterns = django.conf.urls.patterns("",

  # UI - RENDERED FROM TEMPLATES IN INFO REPOSITORY
  ("^/?$", "ui_home.index"),
  ("^learn/$", "ui_home.learn"),
  ("^learn/crossref_faq$", "ui_home.crossref_faq"),
  ("^learn/id_basics$", "ui_home.id_basics"),
  ("^learn/suffix_passthrough$", "ui_home.suffix_passthrough"),
  ("^home/(\w+)$", "ui_home.no_menu"),

  # UI - OTHER
  ("^account/edit$", "ui_account.edit", { "ssl": True }),
  ("^account/pwreset(?P<pwrr>/.*)?$", "ui_account.pwreset", { "ssl": True }),
  ("^admin/?$", "ui_admin.index", { "ssl": True }),
  ("^admin/usage$", "ui_admin.usage", { "ssl": True }),
  ("^admin/manage_users$", "ui_admin.manage_users", { "ssl": True }),
  ("^admin/add_user$", "ui_admin.add_user", { "ssl": True }),
  ("^admin/manage_groups$", "ui_admin.manage_groups", { "ssl": True }),
  ("^admin/add_group$", "ui_admin.add_group", { "ssl": True }),
  ("^admin/system_status$", "ui_admin.system_status", { "ssl": True }),
  ("^admin/ajax_system_status$", "ui_admin.ajax_system_status"),
  ("^admin/alert_message$", "ui_admin.alert_message", { "ssl": True }),
  ("^ajax_hide_alert$", "ui.ajax_hide_alert"),
  ("^contact$", "ui.contact"),
  ("^create/?$", "ui_create.index"),
  ("^create/simple$", "ui_create.simple"),
  ("^create/advanced$", "ui_create.advanced"),
  ("^demo/?$", "ui_demo.index"),
  ("^demo/simple$", "ui_demo.simple"),
  ("^demo/advanced$", "ui_demo.advanced"),
  ("^doc/\w[\w.]*\\.(?:html|py)$", "ui.doc"),
  ("^i18n/", include('django.conf.urls.i18n')),
  ("^lookup/?$", "ui_lookup.index"),
  ("^manage/?$", "ui_manage.index"),
  ("^manage/edit/(.*)", "ui_manage.edit"),
  ("^manage/display_xml/(.*)", "ui_manage.display_xml"),
  ("^new_account$", "ui_admin.new_account", { "ssl": True }),
  ("^search/?$", "ui_search.index"),
  ("^search/results$", "ui_search.results"),
  ("^tombstone/id/", "ui.tombstone"),

  # SHARED BETWEEN UI AND API
  ("^id/", "dispatch.d", { "uiFunction": "ui_manage.details",
    "apiFunction": "api.identifierDispatcher" }),
  ("^login$", "dispatch.d", { "uiFunction": "ui_account.login",
    "apiFunction": "api.login", "ssl": True }),
  ("^logout$", "dispatch.d", { "uiFunction": "ui_account.logout",
    "apiFunction": "api.logout" }),

  # API
  ("^shoulder/", "api.mintIdentifier"),
  ("^status$", "api.getStatus"),
  ("^version$", "api.getVersion"),
  ("^download_request$", "api.batchDownloadRequest"),
  ("^admin/pause$", "api.pause"),
  ("^admin/reload$", "api.reload"),

  # OAI
  ("^oai$", "oai.dispatch")

)

if django.conf.settings.STANDALONE:
  urlpatterns += django.conf.urls.patterns("",
    ("^static/(?P<path>.*)$", "django.views.static.serve",
      { "document_root": django.conf.settings.MEDIA_ROOT }),
    ("^download/(?P<path>.*)$", "django.views.static.serve",
      { "document_root": django.conf.settings.DOWNLOAD_PUBLIC_DIR }))

handler404 = "django.views.defaults.page_not_found"
handler500 = "django.views.defaults.server_error"
