import django.views.defaults
import django.conf
import django.conf.urls.i18n
from django.conf.urls import url, include
from django.conf.urls.i18n import i18n_patterns
from django.views.i18n import JavaScriptCatalog

import django.views.static

import api
import dispatch
import oai
import ui
import ui_account
import ui_admin
import ui_create
import ui_demo
import ui_home

import ezidapp.admin

import ui_manage
import ui_search

urlpatterns = i18n_patterns(
    # path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    # url("^i18n/", include(django.conf.urls.i18n), name="i18n"),
    url("^i18n/", JavaScriptCatalog.as_view(), name='i18n'),
    # url("jsi18n/", JavaScriptCatalog.as_view(), name='javascript-catalog'),

    # url("^$", ui_home.inde, name="ui_home.index)
    # UI - RENDERED FROM TEMPLATES IN INFO REPOSITORY
    url("^$", ui_home.index, name="ui_home.index"),
    url("^learn/$", ui_home.learn, name="ui_home.learn"),
    url("^learn/ark_open_faq$", ui_home.ark_open_faq, name="ui_home.ark_open_faq"),
    url("^learn/crossref_faq$", ui_home.crossref_faq, name="ui_home.crossref_faq"),
    url(
        "^learn/doi_services_faq$",
        ui_home.doi_services_faq,
        name="ui_home.doi_services_faq",
    ),
    url("^learn/id_basics$", ui_home.id_basics, name="ui_home.id_basics"),
    url("^learn/id_concepts$", ui_home.id_concepts, name="ui_home.id_concepts"),
    url("^learn/open_source$", ui_home.open_source, name="ui_home.open_source"),
    url(
        "^learn/suffix_passthrough$",
        ui_home.suffix_passthrough,
        name="ui_home.suffix_passthrough",
    ),
    url("^home/(\w+)$", ui_home.no_menu, name="ui_home.no_menu"),
    # UI - OTHER
    url("^account/edit$", ui_account.edit, name="ui_account.edit"),
    url(
        "^account/pwreset(?P<pwrr>/.*)?$", ui_account.pwreset, name="ui_account.pwreset"
    ),
    url("^ajax_hide_alert$", ui.ajax_hide_alert, name="ui.ajax_hide_alert"),
    url("^contact$", ui.contact, name="ui.contact"),
    url("^create/?$", ui_create.index, name="ui_create.index"),
    url("^create/simple$", ui_create.simple, name="ui_create.simple"),
    url("^create/advanced$", ui_create.advanced, name="ui_create.advanced"),
    url("^dashboard/?$", ui_admin.dashboard, name="ui_admin.dashboard"),
    url(
        "^dashboard/ajax_table",
        ui_admin.ajax_dashboard_table,
        name="ui_admin.ajax_dashboard_table",
    ),
    url("^dashboard/csv_stats$", ui_admin.csvStats, name="ui_admin.csvStats"),
    url("^demo/?$", ui_demo.index, name="ui_demo.index"),
    url("^demo/simple$", ui_demo.simple, name="ui_demo.simple"),
    url("^demo/advanced$", ui_demo.advanced, name="ui_demo.advanced"),
    url("^doc/[-\w.]*\\.(?:html|py|sh)$", ui.doc, name="ui.doc"),
    url("^download_confirm$", ui_manage.download, name="ui_manage.download"),
    url("^download_error$", ui_manage.download_error, name="ui_manage.download_error"),

    url("^manage/?$", ui_manage.index, name="ui_manage.index"),
    url("^manage/edit/(.*)", ui_manage.edit, name="ui_manage.edit"),
    url(
        "^manage/display_xml/(.*)", ui_manage.display_xml, name="ui_manage.display_xml"
    ),
    url("^search/?$", ui_search.index, name="ui_search.index"),
    url("^search/results$", ui_search.results, name="ui_search.results"),
    url("^tombstone/id/", ui.tombstone, name="ui.tombstone"),
    # SHARED BETWEEN UI AND API
    url(
        "^id/",
        dispatch.d,
        {"uiFunction": ui_manage.details, "apiFunction": api.identifierDispatcher},
    ),
    url(
        "^login$",
        dispatch.d,
        {"uiFunction": ui_account.login, "apiFunction": api.login},
    ),
    url(
        "^logout$",
        dispatch.d,
        {"uiFunction": ui_account.logout, "apiFunction": api.logout},
    ),
    # API
    url("^shoulder/", api.mintIdentifier, name="api.mintIdentifier"),
    url("^status$", api.getStatus, name="api.getStatus"),
    url("^version$", api.getVersion, name="api.getVersion"),
    url(
        "^download_request$", api.batchDownloadRequest, name="api.batchDownloadRequest"
    ),
    url("^admin/pause$", api.pause, name="api.pause"),
    url("^admin/reload$", api.reload, name="api.reload"),
    # OAI
    url("^oai$", oai.dispatch, name="oai.dispatch"),
    # ADMIN
    url("^admin/login/?$", ui_account.login, name="ui_account.login"),
    url("^admin/logout/?$", ui_account.logout, name="ui_account.logout"),
    prefix_default_language=False
)
    # url(
    #     "^admin/", include(ezidapp.admin.superuser.urls) # RD
    # ),
# ]

if django.conf.settings.STANDALONE:
    urlpatterns.extend(
        [
            url(
                "^static/(?P<path>.*)$",
                django.views.static.serve,
                {"document_root": django.conf.settings.STATIC_ROOT},
            ),
            url(
                "^download/(?P<path>.*)$",
                django.views.static.serve,
                {"document_root": django.conf.settings.DOWNLOAD_PUBLIC_DIR},
            ),
        ]
    )

handler404 = django.views.defaults.page_not_found
handler500 = django.views.defaults.server_error
