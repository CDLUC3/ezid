#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import django.conf
import urllib.error
import urllib.parse
import urllib.request
import urllib.response

import django.shortcuts
import django.template.loader

import impl.ui_common
import impl.ui_create


# noinspection PyDictCreation
def index(request):
    if request.method not in ["GET", "POST"]:
        return impl.ui_common.methodNotAllowed(request)
    d = {'menu_item': 'ui_home.index'}
    d['prefixes'] = sorted(
        django.conf.settings.TEST_SHOULDER_DICT, key=lambda p: p['namespace'].lower()
    )
    d['form_placeholder'] = True
    d = impl.ui_create.simple_form(request, d)
    result = d['id_gen_result']
    if result == 'edit_page':
        # noinspection PyUnresolvedReferences
        return impl.ui_common.render(request, 'index', d)  # ID Creation page
    elif result == 'bad_request':
        return impl.ui_common.badRequest(request)
    elif result.startswith('created_identifier:'):
        return django.shortcuts.redirect(
            "/id/" + urllib.parse.quote(result.split()[1], ":/")
        )  # ID Details page

def ajax_index_form(request):
    if request.method not in ["GET"]:
        return impl.ui_common.methodNotAllowed(request)
    d = {'menu_item': 'ui_home.index'}
    d['prefixes'] = sorted(
        django.conf.settings.TEST_SHOULDER_DICT, key=lambda p: p['namespace'].lower()
    )
    d['form_placeholder'] = True  # is this necessary?
    d = impl.ui_create.simple_form(request, d)
    result = d['id_gen_result']
    if result == 'edit_page':
        # noinspection PyUnresolvedReferences
        # return impl.ui_common.render(request, 'index', d)  # ID Creation page
        return impl.ui_common.render(request, 'create/_home_demo_form', d)
        # return render(request, 'create/home_demo_form.html', d)
    elif result == 'bad_request':
        return impl.ui_common.badRequest(request)


def learn(request):
    if request.method != "GET":
        return impl.ui_common.methodNotAllowed(request)
    d = {'menu_item': 'ui_home.learn'}
    # noinspection PyUnresolvedReferences
    return impl.ui_common.render(request, 'learn', d)


def ark_open_faq(request):
    if request.method != "GET":
        return impl.ui_common.methodNotAllowed(request)
    d = {'menu_item': 'ui_home.learn'}
    # noinspection PyUnresolvedReferences
    return impl.ui_common.render(request, 'info/ark_open_faq', d)


def crossref_faq(request):
    if request.method != "GET":
        return impl.ui_common.methodNotAllowed(request)
    d = {'menu_item': 'ui_home.learn'}
    # noinspection PyUnresolvedReferences
    return impl.ui_common.render(request, 'info/crossref_faq', d)


def doi_services_faq(request):
    if request.method != "GET":
        return impl.ui_common.methodNotAllowed(request)
    d = {'menu_item': 'ui_home.learn'}
    # noinspection PyUnresolvedReferences
    return impl.ui_common.render(request, 'info/doi_services_faq', d)


def id_basics(request):
    if request.method != "GET":
        return impl.ui_common.methodNotAllowed(request)
    d = {'menu_item': 'ui_home.learn'}
    # noinspection PyUnresolvedReferences
    return impl.ui_common.render(request, 'info/id_basics', d)


def id_concepts(request):
    if request.method != "GET":
        return impl.ui_common.methodNotAllowed(request)
    d = {'menu_item': 'ui_home.learn'}
    # noinspection PyUnresolvedReferences
    return impl.ui_common.render(request, 'info/id_concepts', d)


def open_source(request):
    if request.method != "GET":
        return impl.ui_common.methodNotAllowed(request)
    d = {'menu_item': 'ui_home.learn'}
    # noinspection PyUnresolvedReferences
    return impl.ui_common.render(request, 'info/open_source', d)


def suffix_passthrough(request):
    if request.method != "GET":
        return impl.ui_common.methodNotAllowed(request)
    d = {'menu_item': 'ui_home.learn'}
    # noinspection PyUnresolvedReferences
    return impl.ui_common.render(request, 'info/suffix_passthrough', d)


def no_menu(request, template_name):
    if request.method != "GET":
        return impl.ui_common.methodNotAllowed(request)
    d = {'menu_item': 'ui_home.null'}
    try:
        django.template.loader.get_template('info/' + template_name + ".html")
    except Exception:
        return impl.ui_common.error(request, 404)
    return impl.ui_common.render(request, 'info/' + template_name, d)
