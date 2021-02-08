import django.views.defaults
import django.conf
import django.conf.urls.i18n
import django.views.i18n

import django.views.static

import impl.api
import impl.dispatch
import impl.oai
import impl.ui
import impl.ui_account
import impl.ui_admin
import impl.ui_create
import impl.ui_demo
import impl.ui_home
import impl.ui_manage
import impl.ui_search

import ezidapp.admin

urlpatterns = django.conf.urls.i18n.i18n_patterns(
    # path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    # url("^i18n/", include(django.conf.urls.i18n), name="i18n"),
    django.conf.urls.url(
        "^i18n/", django.views.i18n.JavaScriptCatalog.as_view(), name='i18n'
    ),
    # url("jsi18n/", JavaScriptCatalog.as_view(), name='javascript-catalog'),
    # url("^$", ui_home.inde, name="ui_home.index)
    # UI - RENDERED FROM TEMPLATES IN INFO REPOSITORY
    django.conf.urls.url("^$", impl.ui_home.index, name="ui_home.index"),
    django.conf.urls.url("^learn/$", impl.ui_home.learn, name="ui_home.learn"),
    django.conf.urls.url(
        "^learn/ark_open_faq$", impl.ui_home.ark_open_faq, name="ui_home.ark_open_faq"
    ),
    django.conf.urls.url(
        "^learn/crossref_faq$", impl.ui_home.crossref_faq, name="ui_home.crossref_faq"
    ),
    django.conf.urls.url(
        "^learn/doi_services_faq$",
        impl.ui_home.doi_services_faq,
        name="ui_home.doi_services_faq",
    ),
    django.conf.urls.url(
        "^learn/id_basics$", impl.ui_home.id_basics, name="ui_home.id_basics"
    ),
    django.conf.urls.url(
        "^learn/id_concepts$", impl.ui_home.id_concepts, name="ui_home.id_concepts"
    ),
    django.conf.urls.url(
        "^learn/open_source$", impl.ui_home.open_source, name="ui_home.open_source"
    ),
    django.conf.urls.url(
        "^learn/suffix_passthrough$",
        impl.ui_home.suffix_passthrough,
        name="ui_home.suffix_passthrough",
    ),
    django.conf.urls.url("^home/(\w+)$", impl.ui_home.no_menu, name="ui_home.no_menu"),
    # UI - OTHER
    django.conf.urls.url(
        "^account/edit$", impl.ui_account.edit, name="ui_account.edit"
    ),
    django.conf.urls.url(
        "^account/pwreset(?P<pwrr>/.*)?$",
        impl.ui_account.pwreset,
        name="ui_account.pwreset",
    ),
    django.conf.urls.url(
        "^ajax_hide_alert$", impl.ui.ajax_hide_alert, name="ui.ajax_hide_alert"
    ),
    django.conf.urls.url("^contact$", impl.ui.contact, name="ui.contact"),
    django.conf.urls.url("^create/?$", impl.ui_create.index, name="ui_create.index"),
    django.conf.urls.url(
        "^create/simple$", impl.ui_create.simple, name="ui_create.simple"
    ),
    django.conf.urls.url(
        "^create/advanced$", impl.ui_create.advanced, name="ui_create.advanced"
    ),
    django.conf.urls.url(
        "^dashboard/?$", impl.ui_admin.dashboard, name="ui_admin.dashboard"
    ),
    django.conf.urls.url(
        "^dashboard/ajax_table",
        impl.ui_admin.ajax_dashboard_table,
        name="ui_admin.ajax_dashboard_table",
    ),
    django.conf.urls.url(
        "^dashboard/csv_stats$", impl.ui_admin.csvStats, name="ui_admin.csvStats"
    ),
    django.conf.urls.url("^demo/?$", impl.ui_demo.index, name="ui_demo.index"),
    django.conf.urls.url("^demo/simple$", impl.ui_demo.simple, name="ui_demo.simple"),
    django.conf.urls.url(
        "^demo/advanced$", impl.ui_demo.advanced, name="ui_demo.advanced"
    ),
    django.conf.urls.url("^doc/[-\w.]*\\.(?:html|py|sh)$", impl.ui.doc, name="ui.doc"),
    django.conf.urls.url(
        "^download_confirm$", impl.ui_manage.download, name="ui_manage.download"
    ),
    django.conf.urls.url(
        "^download_error$",
        impl.ui_manage.download_error,
        name="ui_manage.download_error",
    ),
    django.conf.urls.url("^manage/?$", impl.ui_manage.index, name="ui_manage.index"),
    django.conf.urls.url(
        "^manage/edit/(.*)", impl.ui_manage.edit, name="ui_manage.edit"
    ),
    django.conf.urls.url(
        "^manage/display_xml/(.*)",
        impl.ui_manage.display_xml,
        name="ui_manage.display_xml",
    ),
    django.conf.urls.url("^search/?$", impl.ui_search.index, name="ui_search.index"),
    django.conf.urls.url(
        "^search/results$", impl.ui_search.results, name="ui_search.results"
    ),
    django.conf.urls.url("^tombstone/id/", impl.ui.tombstone, name="ui.tombstone"),
    # SHARED BETWEEN UI AND API
    django.conf.urls.url(
        "^id/",
        impl.dispatch.d,
        {
            "uiFunction": impl.ui_manage.details,
            "apiFunction": impl.api.identifierDispatcher,
        },
    ),
    django.conf.urls.url(
        "^login$",
        impl.dispatch.d,
        {"uiFunction": impl.ui_account.login, "apiFunction": impl.api.login},
    ),
    django.conf.urls.url(
        "^logout$",
        impl.dispatch.d,
        {"uiFunction": impl.ui_account.logout, "apiFunction": impl.api.logout},
    ),
    # API
    django.conf.urls.url(
        "^shoulder/", impl.api.mintIdentifier, name="api.mintIdentifier"
    ),
    django.conf.urls.url("^status$", impl.api.getStatus, name="api.getStatus"),
    django.conf.urls.url("^version$", impl.api.getVersion, name="api.getVersion"),
    django.conf.urls.url(
        "^download_request$",
        impl.api.batchDownloadRequest,
        name="api.batchDownloadRequest",
    ),
    django.conf.urls.url("^admin/pause$", impl.api.pause, name="api.pause"),
    django.conf.urls.url("^admin/reload$", impl.api.reload, name="api.reload"),
    # OAI
    django.conf.urls.url("^oai$", impl.oai.dispatch, name="oai.dispatch"),
    # ADMIN
    django.conf.urls.url(
        "^admin/login/?$", impl.ui_account.login, name="ui_account.login"
    ),
    django.conf.urls.url(
        "^admin/logout/?$", impl.ui_account.logout, name="ui_account.logout"
    ),
    django.conf.urls.url(
        "^admin/",
        django.conf.urls.include(ezidapp.admin.superuser.urls),
    ),
    prefix_default_language=False,
)

if django.conf.settings.STANDALONE:
    urlpatterns.extend(
        [
            django.conf.urls.url(
                "^static/(?P<path>.*)$",
                django.views.static.serve,
                {"document_root": django.conf.settings.STATIC_ROOT},
            ),
            django.conf.urls.url(
                "^download/(?P<path>.*)$",
                django.views.static.serve,
                {"document_root": django.conf.settings.DOWNLOAD_PUBLIC_DIR},
            ),
        ]
    )

handler404 = django.views.defaults.page_not_found
handler500 = django.views.defaults.server_error
