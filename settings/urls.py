#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import django.conf.urls
import django.conf.urls.static
import django.urls
import django.views.defaults

import ezidapp.admin

# These imports are only used by management commands. As the management commands are not
# imported during initialization of the main server component, we import them here to
# let the main Django service know that these models exist, so that it doesn't try to
# delete the associated tables when generating migrations.
# noinspection PyUnresolvedReferences
import ezidapp.models.link_checker
import ezidapp.models.statistics

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
import impl.monitor

# fmt:off
urlpatterns = [
    # UI - RENDERED FROM TEMPLATES IN INFO REPOSITORY
    django.urls.re_path("^$",                              impl.ui_home.index,                 name="ui_home.index"),
    django.urls.re_path("^home/ajax_index_form$",          impl.ui_home.ajax_index_form,       name="ui_home.ajax_index_form"),
    django.urls.re_path("^learn/$",                        impl.ui_home.learn,                 name="ui_home.learn"),
    django.urls.re_path("^learn/crossref_faq$",            impl.ui_home.crossref_faq,          name="ui_home.crossref_faq"),
    django.urls.re_path("^learn/doi_services_faq$",        impl.ui_home.doi_services_faq,      name="ui_home.doi_services_faq",),
    django.urls.re_path("^learn/id_basics$",               impl.ui_home.id_basics,             name="ui_home.id_basics"),
    django.urls.re_path("^learn/id_concepts$",             impl.ui_home.id_concepts,           name="ui_home.id_concepts"),
    django.urls.re_path("^learn/open_source$",             impl.ui_home.open_source,           name="ui_home.open_source"),
    django.urls.re_path("^learn/suffix_passthrough$",      impl.ui_home.suffix_passthrough,    name="ui_home.suffix_passthrough",),
    django.urls.re_path("^home/(\w+)$",                    impl.ui_home.no_menu,               name="ui_home.no_menu"),
    # UI - OTHER
    django.urls.re_path("^account/edit$",                  impl.ui_account.edit,               name="ui_account.edit"),
    django.urls.re_path("^account/pwreset(?P<pwrr>/.*)?$", impl.ui_account.pwreset,            name="ui_account.pwreset",),
    django.urls.re_path("^ajax_hide_alert$",               impl.ui.ajax_hide_alert,            name="ui.ajax_hide_alert"),
    django.urls.re_path("^contact$",                       impl.ui.contact,                    name="ui.contact"),
    django.urls.re_path("^create/?$",                      impl.ui_create.index,               name="ui_create.index"),
    django.urls.re_path("^create/simple$",                 impl.ui_create.simple,              name="ui_create.simple"),
    django.urls.re_path("^create/advanced$",               impl.ui_create.advanced,            name="ui_create.advanced"),
    django.urls.re_path("^dashboard/?$",                   impl.ui_admin.dashboard,            name="ui_admin.dashboard"),
    django.urls.re_path("^dashboard/ajax_table",           impl.ui_admin.ajax_dashboard_table, name="ui_admin.ajax_dashboard_table",),
    django.urls.re_path("^dashboard/csv_stats$",           impl.ui_admin.csvStats,             name="ui_admin.csvStats"),
    django.urls.re_path("^demo/?$",                        impl.ui_demo.index,                 name="ui_demo.index"),
    django.urls.re_path("^demo/simple$",                   impl.ui_demo.simple,                name="ui_demo.simple"),
    django.urls.re_path("^demo/advanced$",                 impl.ui_demo.advanced,              name="ui_demo.advanced"),
    django.urls.re_path("^doc/[-\w.]*\\.(?:html|py|sh)$",  impl.ui.doc,                        name="ui.doc"),
    django.urls.re_path("^download_confirm$",              impl.ui_manage.download,            name="ui_manage.download"),
    django.urls.re_path("^download_error$",                impl.ui_manage.download_error,      name="ui_manage.download_error",),
    django.urls.re_path("^manage/?$",                      impl.ui_manage.index,               name="ui_manage.index"),
    django.urls.re_path("^manage/edit/(.*)",               impl.ui_manage.edit,                name="ui_manage.edit"),
    django.urls.re_path("^manage/display_xml/(.*)",        impl.ui_manage.display_xml,         name="ui_manage.display_xml",),
    django.urls.re_path("^search/?$",                      impl.ui_search.index,               name="ui_search.index"),
    django.urls.re_path("^search/results$",                impl.ui_search.results,             name="ui_search.results"),
    django.urls.re_path("^tombstone/id/",                  impl.ui.tombstone,                  name="ui.tombstone"),
    # SHARED BETWEEN UI AND API
    django.urls.re_path("^id/",                            impl.dispatch.d,                    {"uiFunction": impl.ui_manage.details, "apiFunction": impl.api.identifierDispatcher,},),
    django.urls.re_path("^login$",                         impl.dispatch.d,                    {"uiFunction": impl.ui_account.login,  "apiFunction": impl.api.login},),
    django.urls.re_path("^logout$",                        impl.dispatch.d,                    {"uiFunction": impl.ui_account.logout, "apiFunction": impl.api.logout},),
    # API
    django.urls.re_path("^(ark:|doi:)(?P<identifier>.*)$", impl.api.resolveIdentifier,         name="api.resolveIdentifier"),
    django.urls.re_path("^shoulder/",                      impl.api.mintIdentifier,            name="api.mintIdentifier"),
    django.urls.re_path("^status$",                        impl.api.getStatus,                 name="api.getStatus"),
    django.urls.re_path("^version$",                       impl.api.getVersion,                name="api.getVersion"),
    django.urls.re_path("^download_request$",              impl.api.batchDownloadRequest,      name="api.batchDownloadRequest",),
    django.urls.re_path("^s3_download/",                   impl.api.s3_download,               name="api.s3_download",), 
    django.urls.re_path("^admin/pause$",                   impl.api.pause,                     name="api.pause"),
    # django.urls.re_path("^admin/reload$",                  impl.api.reload,                    name="api.reload"),
    # OAI
    django.urls.re_path("^oai$",                           impl.oai.dispatch,                  name="oai.dispatch"),
    # ADMIN
    django.urls.re_path("^admin/login/?$",                 impl.ui_account.login,              name="ui_account.login"),
    django.urls.re_path("^admin/logout/?$",                impl.ui_account.logout,             name="ui_account.logout"),
    django.urls.re_path('^admin/',                         ezidapp.admin.superuser.urls),
    # Monitoring
    django.urls.re_path('^monitor/queues',                 impl.monitor.Queues.as_view(),      name='monitor.Queues'),

    # django.urls.re_path("^admin/",                         django.conf.urls.include(ezidapp.admin.superuser.urls)),
    # django.urls.re_path("^admin/",                         ezidapp.admin.superuser.urls),
    # path('admin/', admin.site.urls),
]

if django.conf.settings.STANDALONE:
    urlpatterns.extend([
        django.conf.urls.static.static(django.conf.settings.STATIC_URL, document_root=django.conf.settings.STATIC_ROOT)[0],
        django.conf.urls.static.static('/static/download/public', document_root=django.conf.settings.DAEMONS_DOWNLOAD_PUBLIC_DIR)[0],
    ])
# fmt:on

handler404 = django.views.defaults.page_not_found
handler500 = django.views.defaults.server_error
