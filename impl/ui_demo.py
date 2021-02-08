import django.shortcuts

import impl.ui_common
import impl.ui_create


def index(_request):
    _d = {'menu_item': 'ui_home.learn'}
    return django.shortcuts.redirect("ui_demo.simple")


# noinspection PyDictCreation
def simple(request):
    d = {'menu_item': 'ui_home.learn'}
    d["testPrefixes"] = impl.ui_common.testPrefixes
    d['prefixes'] = sorted(
        impl.ui_common.testPrefixes, key=lambda p: p['namespace'].lower()
    )  # must be done before calling form processing
    d = impl.ui_create.simple_form(request, d)
    return impl.ui_common.renderIdPage(request, 'demo/simple', d)


# noinspection PyDictCreation
def advanced(request):
    d = {'menu_item': 'ui_home.learn'}
    d["testPrefixes"] = impl.ui_common.testPrefixes
    d['prefixes'] = sorted(
        impl.ui_common.testPrefixes, key=lambda p: p['namespace'].lower()
    )  # must be done before calling form processing
    d = impl.ui_create.adv_form(request, d)
    return impl.ui_common.renderIdPage(request, 'demo/advanced', d)
