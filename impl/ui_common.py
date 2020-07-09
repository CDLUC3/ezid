from pprint import pprint

import django.conf
import django.contrib.messages
import django.http
import django.template
import django.template.loader
import django.utils.http
import os
import re
import string
import urllib
from random import choice

import config
import ezidapp.models
import newsfeed
import userauth
import urlparse

from django.utils import safestring
from django.utils.translation import ugettext as _

ezidUrl = None
templates = None  # { name: (template, path), ... }
alertMessage = None
testPrefixes = None
google_analytics_id = None
reload_templates = None

manual_profiles = {"datacite_xml": "DataCite"}


def loadConfig():
    # these aren't really globals for the whole app, but globals for ui_common
    # outside of this module, use ui_common.varname
    global ezidUrl, templates, alertMessage, testPrefixes
    global google_analytics_id
    global reload_templates
    ezidUrl = config.get("DEFAULT.ezid_base_url")
    templates = {}
    _load_templates([d for t in django.conf.settings.TEMPLATES for d in t["DIRS"]])
    alertMessage = ezidapp.models.getAlertMessage()
    reload_templates = hasattr(django.conf.settings, "RELOAD_TEMPLATES")
    if reload_templates:
        reload_templates = django.conf.settings.RELOAD_TEMPLATES
    testPrefixes = []
    p = ezidapp.models.getArkTestShoulder()
    testPrefixes.append({"namespace": p.name, "prefix": p.prefix})
    p = ezidapp.models.getDoiTestShoulder()
    testPrefixes.append({"namespace": p.name, "prefix": p.prefix})
    google_analytics_id = config.get("DEFAULT.google_analytics_id")


# loads the templates directory recursively (dir_list is a list)
def _load_templates(dir_list):
    global templates
    my_dir = apply(os.path.join, dir_list)
    for f in os.listdir(my_dir):
        if os.path.isdir(os.path.join(my_dir, f)):
            _load_templates(dir_list + [f])
        elif os.path.isfile(os.path.join(my_dir, f)) and f.endswith(".html"):
            local_path = apply(os.path.join, dir_list[1:] + [f])
            templates[local_path[:-5]] = (
                django.template.loader.get_template(local_path),
                local_path,
            )


def render(request, template, context={}):
    global alertMessage, google_analytics_id, reload_templates

    c = {
        "session": request.session,
        "authenticatedUser": userauth.getUser(request),
        "alertMessage": alertMessage,
        "feed_cache": newsfeed.getLatestItems(),
        "google_analytics_id": google_analytics_id,
        "debug": django.conf.settings.DEBUG,
    }
    c.update(context)

    # this is to keep from having to restart the server every 3 seconds
    # to see template changes in development, only reloads if set for optimal performance
    if reload_templates:
        templ = django.template.loader.get_template(templates[template][1])
    else:
        templ = templates[template][0]
    # content = templ.render(django.template.RequestContext(request, c))

    # TODO: Remove this temporary workaround and modify dynamically generated HTML
    # instead.
    templ.backend.engine.autoescape = False

    content = templ.render(c, request)

    # By setting the content type ourselves, we gain control over the
    # character encoding and can properly set the content length.
    ec = content.encode("UTF-8")
    r = django.http.HttpResponse(ec, content_type="text/html; charset=UTF-8")
    r["Content-Length"] = len(ec)
    return r


def renderIdPage(request, path, d):
    """
  Used by Create and Demo ID pages.
  path is string of one of the following '[create|demo]/[simple|advanced]'.
  d['id_gen_result'] will be either 'method_not_allowed', 'bad_request', 'edit_page' or
  'created_identifier: <new_id>'
  """
    result = "edit_page" if "id_gen_result" not in d else d["id_gen_result"]
    if result == "edit_page":
        return render(request, path, d)  # ID Create or Demo page (Simple or Advanced)
    elif d["id_gen_result"] == "bad_request":
        return badRequest(request)
    elif d["id_gen_result"] == "method_not_allowed":
        return methodNotAllowed(request)
    elif d["id_gen_result"].startswith("created_identifier:"):
        return redirect(
            "/id/" + urllib.quote(result.split()[1], ":/")
        )  # ID Details page


def staticHtmlResponse(content):
    r = django.http.HttpResponse(content, content_type="text/html; charset=UTF-8")
    r["Content-Length"] = len(content)
    return r


def staticTextResponse(content):
    r = django.http.HttpResponse(content, content_type="text/plain; charset=UTF-8")
    r["Content-Length"] = len(content)
    return r


def plainTextResponse(message):
    r = django.http.HttpResponse(message, content_type="text/plain")
    r["Content-Length"] = len(message)
    return r


def csvResponse(message, filename):
    r = django.http.HttpResponse(message, content_type="text/csv")
    r["Content-Disposition"] = 'attachment; filename="' + filename + '.csv"'
    return r


# Our development version of Python (2.5) doesn't have the standard
# JSON module (introduced in 2.6), so we provide our own encoder here.

_jsonRe = re.compile('[\\x00-\\x1F"\\\\\\xFF]')


def json(o):
    if type(o) is dict:
        assert all(type(k) is str for k in o), "unexpected object type"
        return "{" + ", ".join(json(k) + ": " + json(v) for k, v in o.items()) + "}"
    elif type(o) is list:
        return "[" + ", ".join(json(v) for v in o) + "]"
    elif type(o) is str or type(o) is unicode:
        return '"' + _jsonRe.sub(lambda c: "\\u%04X" % ord(c.group(0)), o) + '"'
    elif type(o) is bool:
        return "true" if o else "false"
    else:
        assert False, "unexpected object type"


def jsonResponse(data):
    # Per RFC 4627, the default encoding is understood to be UTF-8.
    ec = json(data).encode("UTF-8")
    r = django.http.HttpResponse(ec, content_type="application/json")
    r["Content-Length"] = len(ec)
    return r


redirect = django.http.HttpResponseRedirect


def error(request, code, content_custom=None):
    global alertMessage, google_analytics_id
    t = django.template.RequestContext(
        request,
        {
            "menu_item": "ui_home.null",
            "session": request.session,
            "alertMessage": alertMessage,
            "feed_cache": newsfeed.getLatestItems(),
            "google_analytics_id": google_analytics_id,
            "content_custom": content_custom,
        },
    )
    content = templates[str(code)][0].render(t)
    return django.http.HttpResponse(content, status=code)


def badRequest(request):
    return error(request, 400)


def unauthorized(request):
    return error(request, 401)


def methodNotAllowed(request):
    return error(request, 405)


def formatError(message):
    for p in [_("error: bad request - "), _("error: ")]:
        if message.startswith(p) and len(message) > len(p):
            return message[len(p)].upper() + message[len(p) + 1 :] + "."
    return message


def assembleUpdateDictionary(request, profile, additionalElements={}):
    d = {"_profile": profile.name}
    for e in profile.elements:
        if e.name in request.POST:
            d[e.name] = request.POST[e.name]
    d.update(additionalElements)
    return d


def extract(d, keys):
    """Gets subset of dictionary based on keys in an array"""
    return dict((k, d[k]) for k in keys if k in d)


def random_password(size=8):
    return "".join([choice(string.letters + string.digits) for i in range(size)])


def user_login_required(f):
    """defining a decorator to require a user to be logged in"""

    def wrap(request, *args, **kwargs):
        if userauth.getUser(request) == None:
            django.contrib.messages.error(
                request, _("You must be logged in to view this page.")
            )
            return django.http.HttpResponseRedirect(
                "/login?next=" + django.utils.http.urlquote(request.get_full_path())
            )
        return f(request, *args, **kwargs)

    wrap.__doc__ = f.__doc__
    wrap.__name__ = f.__name__
    return wrap


def admin_login_required(f):
    """defining a decorator to require an admin to be logged in"""

    def wrap(request, *args, **kwargs):
        if not userauth.getUser(request, returnAnonymous=True).isSuperuser:
            django.contrib.messages.error(
                request,
                _("You must be logged in as an administrator to view this page."),
            )
            return django.http.HttpResponseRedirect(
                "/login?next=" + django.utils.http.urlquote(request.get_full_path())
            )
        return f(request, *args, **kwargs)

    wrap.__doc__ = f.__doc__
    wrap.__name__ = f.__name__
    return wrap


def identifier_has_block_data(identifier):
    """
  Returns true if the identifier has block metadata, which affects
  both the display and the editability of the metadata in the UI.
  """
    return (identifier["_profile"] == "erc" and "erc" in identifier) or (
        identifier["_profile"] == "datacite" and "datacite" in identifier
    )


def owner_names(user, page):
    """
  Menu filter/selector used on Manage and Dashboard pages
  Generates a data structure to represent heirarchy of realm -> group -> user, eg:
  [('realm_cdl',        'realm: cdl'),
   ('group_groupname',  ' [groupname]  American Astronomical Society'),
   ('user_username',    '  [username]   American Astronomical Society (by proxy)', ...

  Note: At the time of writing, is it not possible to search for all identifiers
    within a realm or entirety of EZID. But it is possible to aggregate stats for the
    Dashboard at this level. Thus diff't choices available based on page "dashboard"
    or "manage"
  """
    r = []
    me = _userList([user], 0, "  (" + _("me") + ")")
    if user.isSuperuser:
        r += me if page == "manage" else [("all", "ALL EZID")]
        for realm in ezidapp.models.StoreRealm.objects.all().order_by("name"):
            n = realm.name
            r += [("realm_" + n, "Realm: " + n)]
            r += _getGroupsUsers(user, 1, realm.groups.all().order_by("groupname"))
    elif user.isRealmAdministrator:
        r += (
            me
            if page == "manage"
            else [("realm_" + user.realm.name, "All " + user.realm.name)]
        )
        r += _getGroupsUsers(user, 0, user.realm.groups.all().order_by("groupname"))
    else:
        my_proxies = _userList(user.proxy_for.all(), 0, "  (" + _("by proxy") + ")")
        r += me
        if user.isGroupAdministrator:
            r += [
                (
                    "group_" + user.group.groupname,
                    "["
                    + user.group.groupname
                    + "]&nbsp;&nbsp;"
                    + _("Group")
                    + ": "
                    + user.group.organizationName,
                )
            ]
            r += _getUsersInGroup(user, 1, user.group.groupname)
        else:
            r += my_proxies
    return r


def _indent_str(size):
    return "".join(["&nbsp;&nbsp;&nbsp;"] * size)


def _getGroupsUsers(me, indent, groups):
    """ Return heirarchical list of all groups and their constituent users """
    r = []
    for g in groups:
        n = g.groupname
        r += [
            (
                "group_" + n,
                _indent_str(indent)
                + "["
                + n
                + "]&nbsp;&nbsp;"
                + _("Group")
                + ": "
                + g.organizationName,
            )
        ]
        r += _getUsersInGroup(me, indent + 1, n)
    return r


def _getUsersInGroup(me, indent, groupname):
    """ Display all users in group except group admin """
    g = ezidapp.models.getGroupByGroupname(groupname)
    return _userList(
        [user for user in g.users.all() if user.username != me.username], indent, ""
    )


def _userList(users, indent, suffix):
    """ Display list of sorted tuples as follows:
      [('user_uitesting', '**INDENT**[apitest]  EZID API test account'), ...]
  """
    k = "user_"
    # Make list of three items first so they're sortable by DisplayName
    r = [
        (
            k + u.username,
            _indent_str(indent) + "[" + u.username + "]&nbsp;&nbsp;",
            u.displayName + suffix,
        )
        for u in users
    ]
    r2 = sorted(r, key=lambda p: p[2].lower())
    return [(x[0], x[1] + x[2]) for x in r2]  # Concat 2nd and 3rd items


def getOwnerOrGroupOrRealm(ownerkey):
    """
  Takes ownerkey like 'user_uitesting' or 'group_merritt' or 'realm_purdue'
  and returns as tuple of user_id, group_id, realm_id
  """
    if ownerkey is None:
        # ToDo: Is this insecure?
        return ("all", None, None)
    elif ownerkey.startswith("realm_"):
        return (None, None, ownerkey[6:])
    else:
        return getOwnerOrGroup(ownerkey) + (None,)


def getOwnerOrGroup(ownerkey):
    """
  Takes ownerkey like 'user_uitesting' or 'group_merritt'
  and returns as tuple of user_id, group_id
  Note: At the time of writing, is it not possible to search for all identifiers
    within a realm or entirety of EZID. But once it is, use of this function can be
    replaced by getOwnerOrGroupOrRealm
  """
    user_id, group_id = None, None
    if ownerkey is None:
        # ToDo: Is this insecure?
        user_id = "all"
    elif ownerkey.startswith("user_"):
        user_id = ownerkey[5:]
    elif ownerkey.startswith("group_"):
        group_id = ownerkey[6:]
    else:
        user_id = ownerkey
    return (user_id, group_id)


def isEmptyStr(v):
    """ check for any empty string """
    return False if v is not None and v != "" and not v.isspace() else True
