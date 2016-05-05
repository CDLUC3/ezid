import django.conf
import django.conf.urls

import ezidapp.admin

SSL = { "ssl": True }

urlpatterns = django.conf.urls.patterns("",

  # UI - RENDERED FROM TEMPLATES IN INFO REPOSITORY
  ("^/?$", "ui_home.index"),
  ("^home/why$", "ui_home.why"),
  ("^home/understanding$", "ui_home.understanding"),
  ("^home/pricing$", "ui_home.pricing"),
  ("^home/documentation$", "ui_home.documentation"),
  ("^home/outreach$", "ui_home.outreach"),
  ("^home/community$", "ui_home.community"),
  ("^home/(\w+)$", "ui_home.no_menu"),

  # UI - OTHER
  ("^manage/?$", "ui_manage.index"),
  ("^manage/edit/(.*)", "ui_manage.edit"),
  ("^manage/display_xml/(.*)", "ui_manage.display_xml"),
  ("^create/?$", "ui_create.index"),
  ("^create/simple$", "ui_create.simple"),
  ("^create/advanced$", "ui_create.advanced"),
  ("^create/ajax_advanced", "ui_create.ajax_advanced"),
  ("^lookup/?$", "ui_lookup.index"),
  ("^demo/?$", "ui_demo.index"),
  ("^demo/simple$", "ui_demo.simple"),
  ("^demo/advanced$", "ui_demo.advanced"),
  ("^admin-old/?$", "ui_admin.index", SSL),
  ("^admin-old/usage$", "ui_admin.usage", SSL),
  ("^account/edit$", "ui_account.edit", SSL),
  ("^account/pwreset(?P<pwrr>/.*)?$", "ui_account.pwreset", SSL),
  ("^ajax_hide_alert$", "ui.ajax_hide_alert"),
  ("^contact$", "ui.contact"),
  ("^doc/[-\w.]*\\.(?:html|py)$", "ui.doc"),
  ("^tombstone/id/", "ui.tombstone"),

  # SHARED BETWEEN UI AND API
  ("^id/", "dispatch.d", { "uiFunction": "ui_manage.details",
    "apiFunction": "api.identifierDispatcher" }),
  ("^login$", "dispatch.d", dict({ "uiFunction": "ui_account.login",
    "apiFunction": "api.login" }, **SSL)),
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
  ("^oai$", "oai.dispatch"),

  # ADMIN
  ("^admin/login/?$", "ui_account.login", SSL),
  ("^admin/logout/?$", "ui_account.logout"),
  django.conf.urls.url("^admin/",
    django.conf.urls.include(ezidapp.admin.superuser.urls), SSL)

)

if django.conf.settings.STANDALONE:
  urlpatterns += django.conf.urls.patterns("",
    ("^static/(?P<path>.*)$", "django.views.static.serve",
      { "document_root": django.conf.settings.STATIC_ROOT }),
    ("^download/(?P<path>.*)$", "django.views.static.serve",
      { "document_root": django.conf.settings.DOWNLOAD_PUBLIC_DIR }))

handler404 = "django.views.defaults.page_not_found"
handler500 = "django.views.defaults.server_error"
