import ui_common as uic
from django.shortcuts import redirect
import ui_create


def index(request):
    d = {'menu_item': 'ui_home.learn'}
    return redirect("ui_demo.simple")


def simple(request):
    d = {'menu_item': 'ui_home.learn'}
    d["testPrefixes"] = uic.testPrefixes
    d['prefixes'] = sorted(
        uic.testPrefixes, key=lambda p: p['namespace'].lower()
    )  # must be done before calling form processing
    d = ui_create.simple_form(request, d)
    return uic.renderIdPage(request, 'demo/simple', d)


def advanced(request):
    d = {'menu_item': 'ui_home.learn'}
    d["testPrefixes"] = uic.testPrefixes
    d['prefixes'] = sorted(
        uic.testPrefixes, key=lambda p: p['namespace'].lower()
    )  # must be done before calling form processing
    d = ui_create.adv_form(request, d)
    return uic.renderIdPage(request, 'demo/advanced', d)
