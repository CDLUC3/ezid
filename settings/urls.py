import django.conf
import django.conf.urls
from django.conf.urls import include

import ezidapp.admin

urlpatterns = django.conf.urls.patterns("",

  # UI - RENDERED FROM TEMPLATES IN INFO REPOSITORY
  ("^/?$", "ui_home.index"),
  ("^learn/$", "ui_home.learn"),
  ("^learn/crossref_faq$", "ui_home.crossref_faq"),
  ("^learn/id_basics$", "ui_home.id_basics"),
  ("^learn/id_concepts$", "ui_home.id_concepts"),
  ("^learn/open_source$", "ui_home.open_source"),
  ("^learn/suffix_passthrough$", "ui_home.suffix_passthrough"),
  ("^home/(\w+)$", "ui_home.no_menu"),

  # UI - OTHER
  ("^account/edit$", "ui_account.edit", { "ssl": True }),
  ("^account/pwreset(?P<pwrr>/.*)?$", "ui_account.pwreset", { "ssl": True }),
  ("^admin-old/manage_users$", "ui_admin.manage_users", { "ssl": True }),
  ("^admin-old/add_user$", "ui_admin.add_user", { "ssl": True }),
  ("^admin-old/manage_groups$", "ui_admin.manage_groups", { "ssl": True }),
  ("^admin-old/add_group$", "ui_admin.add_group", { "ssl": True }),
  ("^ajax_hide_alert$", "ui.ajax_hide_alert"),
  ("^contact$", "ui.contact"),
  ("^create/?$", "ui_create.index"),
  ("^create/simple$", "ui_create.simple"),
  ("^create/advanced$", "ui_create.advanced"),
  ("^dashboard/?$", "ui_admin.dashboard", { "ssl": True }),
  ("^dashboard/ajax_issues", "ui_admin.ajax_issues", { "ssl": True }),
  ("^demo/?$", "ui_demo.index"),
  ("^demo/simple$", "ui_demo.simple"),
  ("^demo/advanced$", "ui_demo.advanced"),
  ("^doc/[-\w.]*\\.(?:html|py)$", "ui.doc"),
  ("^download_confirm$", "ui_manage.download"),
  ("^download_error$", "ui_manage.download_error"),
  ("^i18n/", include('django.conf.urls.i18n')),
  ("^manage/?$", "ui_manage.index"),
  ("^manage/edit/(.*)", "ui_manage.edit"),
  ("^manage/display_xml/(.*)", "ui_manage.display_xml"),
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
