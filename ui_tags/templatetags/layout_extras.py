#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import operator
import re
import urllib.error
import urllib.parse
import urllib.request
import urllib.response

import django.conf
import django.urls.resolvers
import django.template
import django.template.loader
import django.utils.html
import django.utils.safestring

import impl.util2
import ui_tags.templatetags.decorators

register = django.template.Library()

# settings value
@register.simple_tag
def settings_value(name):
    """Get a value from the settings configuration."""
    try:
        return django.conf.settings.__getattr__(name)
    except AttributeError:
        return ""


@register.simple_tag
def content_heading(heading):
    """Output primary heading at top of page."""
    return (
        '<div class="heading__primary-container">'
        + '<h1 class="heading__primary-text">'
        + str(heading)
        + '</h1></div>'
    )


@register.simple_tag
def choices(name, value, choice_string):
    """Create radio buttons (for simple admin email form) based on string
    choices separated by a pipe."""
    choices = choice_string.split("|")
    return "  ".join(
        [
            '<input type="radio" name="'
            + name
            + '" value="'
            + django.utils.html.escape(x)
            + '"'
            + (' checked="checked"' if value == x else '')
            + '>'
            + django.utils.html.escape(x)
            + '</input>'
            for x in choices
        ]
    )


@register.tag
@ui_tags.templatetags.decorators.basictag(takes_context=True)
def request_value(context, key_name):
    """Output the value of context[key_name], required because normal django
    templating will not retrieve any variables starting with an underscore
    which all of the internal profile variables have."""
    request = context['request']
    if request.method == "GET":
        REQUEST = request.GET
    else:
        REQUEST = request.POST
    if key_name in REQUEST:
        return django.utils.html.escape(REQUEST[key_name])
    else:
        return ''


@register.tag
@ui_tags.templatetags.decorators.basictag(takes_context=True)
def set_dict_value(context, dt, key_name):
    """Set value in the context object equal to the dictionary dt[key_name]"""
    context['value'] = dt[key_name]
    return ''


@register.simple_tag
def get_dict_value(dt, key_name):
    """For getting dictionary values which Django templating can't handle, such
    as those starting with underscore or with a dot in them."""
    if key_name in dt:
        return django.utils.html.escape(dt[key_name])
    else:
        return ''


@register.simple_tag
def identifier_display(id_text, testPrefixes):
    for pre in testPrefixes:
        if id_text.startswith(pre['prefix']):
            return "&#42;&nbsp;" + django.utils.html.escape(id_text)
    return django.utils.html.escape(id_text)


@register.simple_tag
def active_id_display(id_text, _testPrefixes):
    return (
        '<a href="'
        + impl.util2.urlForm(id_text)
        + '">'
        + impl.util2.urlForm(id_text)
        + '</a>'
    )


@register.simple_tag
def help_icon(
    id_of_help, specifics="", css_class="button__icon-help", placement="auto bottom"
):
    """data-container="#' + str(id_of_help)"""
    title = django.utils.safestring.mark_safe(
        "Click for additional help" + " " + str(specifics)
    )
    return django.utils.html.format_html(
        '<a href="#" title="ID type information" class="button__icon-link" id={} role="button" data-toggle="popover" data-placement={} data-trigger="click" tabindex="0">'
        '<img src="/static/images/iconHelp.svg" alt={}  class={} title={}/>'
        '</a>',
        id_of_help,
        placement,
        title,
        css_class,
        title
        # '<a href="#" class="button__icon-link" id="' + str(id_of_help) + '" ' +
        # 'role="button" data-toggle="popover" data-placement="' + placement + '" ' +
        # 'data-trigger="click" tabindex="0">' +
        # '<img src="/static/images/iconHelp.svg" alt="' + str(title) + '"' +
        # ' class="' + str(css_class) + '" title="' + str(title) + '"/></a>'
    )


@register.filter('fieldtype')
def fieldtype(field):
    """Get the type of a django form field (thus helps you know what class to
    apply to it)"""
    return field.field.widget.__class__.__name__


@register.filter(name='add_attributes')
def add_attributes(field, css):
    """Add attributes to a django form field."""
    attrs = {}
    definition = css.split(',')
    for d in definition:
        if ':' not in d:
            attrs['class'] = d
        else:
            t, v = d.split(':')
            attrs[t] = v
    return field.as_widget(attrs=attrs)


@register.tag
@ui_tags.templatetags.decorators.basictag(takes_context=True)
def host_based_include(context, template_path):
    """This includes a file from a different directory instead of the normal
    specified file based on the hostname.

    This allows for some simple branding changes in the templates based
    host name differences
    """
    request = context['request']
    host = request.META.get("HTTP_HOST", "default")
    if host not in django.conf.settings.LOCALIZATIONS:
        host = "default"
    template_path = template_path.replace(
        "/_/", f"/{django.conf.settings.LOCALIZATIONS[host][0]}/"
    )
    t = django.template.loader.get_template(template_path)
    return t.render(context.dicts[3])
    # return t.render(context)


# @register.simple_tag(takes_context=True)
@register.tag
@ui_tags.templatetags.decorators.basictag(takes_context=True)
def form_or_dict_value(context, dict, key_name):
    """Output the value of the dict[key_name] unless request.POST contains the
    data for the item which then overrides the dictionary's value.

    This both fixes problems with normal django templating which will
    not retrieve any keys starting with an underscore and it solves the
    problem of re-POSTed values which were getting clobbered by the
    stored values.  POSTed values should override so people do not lose
    their in-process edits.
    """
    request = context['request']
    if request.POST and key_name in request.POST:
        return django.utils.html.escape(request.POST[key_name])
        # return escape(request['POST'][key_name])
    elif key_name in dict:
        return django.utils.html.escape(dict[key_name])
    else:
        return ''


@register.tag
@ui_tags.templatetags.decorators.basictag(takes_context=True)
def form_or_default(context, key_name, default):
    """Output the value of the reposted value unless it doesn't exist then
    outputs the default value passed in."""
    request = context['request']
    if request.method == "GET":
        REQUEST = request.GET
    else:
        REQUEST = request.POST
    if key_name in REQUEST and REQUEST[key_name] != '':
        return django.utils.html.escape(REQUEST[key_name])
    else:
        return django.utils.html.escape(default)


@register.tag
@ui_tags.templatetags.decorators.basictag(takes_context=True)
def selected_radio(context, request_item, loop_index, item_value):
    """return checked="checked" if this should be the currently selected radio
    button based on matching request data or 1st item and nothing selected."""
    request = context['request']
    if request.method == "GET":
        REQUEST = request.GET
    else:
        REQUEST = request.POST
    if request_item in REQUEST and REQUEST[request_item] == item_value:
        return 'checked="checked"'
    elif request_item not in REQUEST and loop_index == 1:
        return 'checked="checked"'
    else:
        return ''


# noinspection PyDefaultArgument
@register.simple_tag
def shoulder_display(
    prefix_dict, id_type_only="False", testPrefixes=[], sans_namespace="False"
):
    """Three types of display:

    FULL --------------->  Caltech Biology ARK (ark:/77912/w7)) SANS
    NAMESPACE ----->    ARK (ark:/99999/...))       <----------   used
    for demo page ID TYPE ONLY ------->    ARK
    <----------   used for home page
    """
    if id_type_only == "False":
        display_prefix = ""
        for pre in testPrefixes:
            if prefix_dict['prefix'].startswith(pre['prefix']):
                display_prefix = (
                    " (" + django.utils.html.escape(prefix_dict['prefix']) + "/... )"
                )
        if display_prefix == '':
            display_prefix = " (" + prefix_dict['prefix'] + ")"
        if sans_namespace == "True":
            return (
                django.utils.html.escape(_get_id_type(prefix_dict['prefix']))
                + display_prefix
            )
        else:
            type = _get_id_type(prefix_dict['prefix'])
            return (
                django.utils.html.escape(prefix_dict['namespace'] + ' ' + type)
                + display_prefix
            )
    else:
        return django.utils.html.escape(_get_id_type(prefix_dict['prefix']))


def _get_id_type(prefix):
    t = prefix.split(":")[0].upper()
    return t


@register.simple_tag
def unavailable_codes(for_field):
    items = (
        ("unac", "temporarily inaccessible"),
        ("unal", "unallowed, suppressed intentionally"),
        ("unap", "not applicable, makes no sense"),
        ("unas", "value unassigned (e.g., Untitled)"),
        ("unav", "value unavailable, possibly unknown"),
        ("unkn", "known to be unknown (e.g., Anonymous, Inconnue)"),
        ("none", "never had a value, never will"),
        ("null", "explicitly and meaningfully empty"),
        ("tba", "to be assigned or announced later"),
        ("etal", "too numerous to list (et alia)"),
        ("at", "the real value is at the given URL or identifier"),
    )
    return (
        "<ul>"
        + "\n".join(
            [
                '<li><a href="#'
                + django.utils.html.escape(x[0])
                + "_"
                + for_field
                + '" name="code_insert_link">'
                + django.utils.html.escape("(:" + x[0] + ")")
                + "</a> "
                + django.utils.html.escape(x[1])
                + "</li>"
                for x in items
            ]
        )
        + "</ul>"
    )
    # <li><a href="#unas_datacite.creator" name="code_insert_link">(:unac)</a> temporarily inacessible</li>


@register.tag
@ui_tags.templatetags.decorators.basictag(takes_context=True)
def full_url_to_id_details(_context, id_text):
    """return URL form of identifier."""
    return impl.util2.urlForm(id_text)


@register.tag
@ui_tags.templatetags.decorators.basictag(takes_context=True)
def full_url_to_id_details_urlencoded(_context, id_text):
    """return URL form of identifier, URL-encoded."""
    return urllib.parse.quote(impl.util2.urlForm(id_text))


# check for more than one of the same identifer type
# NOT checking for duplicate shoulders, returns t/f
@register.filter(name='duplicate_id_types')
def duplicate_id_types(prefixes):
    kinds = {}
    for prefix in prefixes:
        t = re.search('^[A-Za-z]+:', prefix['prefix'])
        t = t.group(0)[:-1]
        if t in kinds:
            kinds[t] += 1
        else:
            kinds[t] = 1
    for key, value in list(kinds.items()):
        if value > 1:
            return True
    return False


# returns list of unique ID types such as ARK/DOI/UUID with the
# prefix information, ((prefix, prefix_obj), etc)
# should only be called where only one prefix per type
@register.filter(name='unique_id_types')
def unique_id_types(prefixes):
    kinds = {}
    for prefix in prefixes:
        t = re.search('^[A-Za-z]+:', prefix['prefix'])
        t = t.group(0)[:-1]
        kinds[t] = prefix
    i = [
        (
            x[0].upper(),
            x[1],
        )
        for x in list(kinds.items())
    ]
    return sorted(i, key=operator.itemgetter(0))
