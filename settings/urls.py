import django.conf
import django.conf.urls

import ezidapp.admin

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
  ("^admin-old/?$", "ui_admin.index", { "ssl": True }),
  ("^admin-old/usage$", "ui_admin.usage", { "ssl": True }),
  ("^admin-old/manage_users$", "ui_admin.manage_users", { "ssl": True }),
  ("^admin-old/add_user$", "ui_admin.add_user", { "ssl": True }),
  ("^admin-old/manage_groups$", "ui_admin.manage_groups", { "ssl": True }),
  ("^admin-old/add_group$", "ui_admin.add_group", { "ssl": True }),
  ("^account/edit$", "ui_account.edit", { "ssl": True }),
  ("^account/pwreset(?P<pwrr>/.*)?$", "ui_account.pwreset", { "ssl": True }),
  ("^ajax_hide_alert$", "ui.ajax_hide_alert"),
  ("^contact$", "ui.contact"),
  ("^doc/[-\w.]*\\.(?:html|py)$", "ui.doc"),
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
  ("^oai$", "oai.dispatch"),

  # ADMIN
  django.conf.urls.url("^admin/",
    django.conf.urls.include(ezidapp.admin.superuser.urls), { "ssl": True })

)

if django.conf.settings.STANDALONE:
  urlpatterns += django.conf.urls.patterns("",
    ("^static/(?P<path>.*)$", "django.views.static.serve",
      { "document_root": django.conf.settings.STATIC_ROOT }),
    ("^download/(?P<path>.*)$", "django.views.static.serve",
      { "document_root": django.conf.settings.DOWNLOAD_PUBLIC_DIR }))

handler404 = "django.views.defaults.page_not_found"
handler500 = "django.views.defaults.server_error"
