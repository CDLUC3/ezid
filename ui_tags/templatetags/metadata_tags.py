#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import time

import django.conf
import django.template
import django.utils.html

import ui_tags.templatetags.decorators
import ui_tags.templatetags.layout_extras

register = django.template.Library()


@register.simple_tag
def display_value(id_dictionary, element):
    """Takes the id metadata dictionary and element object."""
    if element.name in id_dictionary:
        return display_formatted(id_dictionary, element)
    else:
        return '[No value]'


def display_formatted(id_dictionary, element):
    """formats the element object according to its display style."""
    if element.displayType == 'datetime':
        t = time.gmtime(float(id_dictionary[element.name]))
        return time.strftime(django.conf.settings.TIME_FORMAT_UI_METADATA, t) + " UTC"
    elif element.displayType == 'url':
        return (
            "<a href='"
            + id_dictionary[element.name]
            + "'>"
            + django.utils.html.escape(id_dictionary[element.name])
            + "</a>"
        )
    elif element.displayType == 'boolean':
        if (
            id_dictionary[element.name].upper() == 'TRUE'
            or id_dictionary[element.name].upper() == "YES"
        ):
            return 'Yes'
        else:
            return 'No'
    elif element.displayType == 'is_public':
        if id_dictionary[element.name] == 'public':
            return 'Yes'
        else:
            return 'No'
    else:
        return django.utils.html.escape(id_dictionary[element.name])


@register.tag
@ui_tags.templatetags.decorators.basictag(takes_context=True)
def display_form_element(context, element, id_object=None):
    """Displays a form element as indicated in the profile.

    Automatically pulls re-POSTed values and object (optional)
    """
    if element.displayType.startswith('text'):
        return display_text_box(context, element, id_object)
    elif element.displayType.startswith('select:'):
        opts = eval(element.displayType[len('select:') :])
        return display_select(context, element, opts, id_object)
    return ''


def display_text_box(context, element, id_object):
    """displays a text box based on the element."""
    # noinspection PyUnresolvedReferences
    return '<input type="text" class="{} form-control" name="{}" id="{}" value="{}" />'.format(
        *tuple(
            [
                django.utils.html.escape(x)
                for x in (
                    ui_tags.templatetags.layout_extras.tooltip_class(element.name),
                    element.name,
                    element.name,
                    _form_value(context, element.name, id_object),
                )
            ]
        )
    )


def display_select(context, element, options, id_object):
    """displays a select list based on the element."""
    # noinspection PyUnresolvedReferences
    sel_part = '<select class="{} form-control" name="{}" id="{}">'.format(
        ui_tags.templatetags.layout_extras.tooltip_class(element.name),
        element.name,
        element.name,
    )
    selected = _form_value(context, element.name, id_object)
    return (
        sel_part
        + ''.join(
            [
                (
                    '<option value="'
                    + django.utils.html.escape(x[0])
                    + '" '
                    + ('selected="selected"' if x[0] == selected else '')
                    + ">"
                    + django.utils.html.escape(x[1])
                    + "</option>"
                )
                for x in options
            ]
        )
        + "</select>"
    )


def _request_value(context, key_name):
    """gets the value of context[key_name]"""
    request = context['request']
    if request.method == "GET":
        REQUEST = request.GET
    else:
        REQUEST = request.POST
    if key_name in REQUEST:
        return REQUEST[key_name]
    else:
        return ''


def _form_value(context, key_name, id_object):
    """Gets a value in this priority 1) request, 2) id_object, 3) default of
    ''."""
    val = ''
    if id_object is not None and key_name in id_object:
        val = id_object[key_name]
    request = context['request']
    if request.method == "GET":
        REQUEST = request.GET
    else:
        REQUEST = request.POST
    if key_name in REQUEST:
        val = REQUEST[key_name]
    return val
