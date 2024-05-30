#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import hashlib
import json
import logging
import operator
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.response

import django.conf
import django.contrib.messages
import django.core.mail
import django.core.validators
import django.db.transaction
import django.http
import django.shortcuts
import django.urls.resolvers
import django.utils.http
from django.utils.translation import gettext as _

import ezidapp.admin
import ezidapp.models.user
import ezidapp.models.util
import impl.form_objects
import impl.ui_common
import impl.userauth

ACCOUNT_FIELDS_EDITABLE = [
    'primaryContactName',
    'primaryContactEmail',
    'primaryContactPhone',
    'secondaryContactName',
    'secondaryContactEmail',
    'secondaryContactPhone',
    'accountDisplayName',
    'accountEmail',
]

proxies_default = _("None chosen")

log = logging.getLogger(__name__)


def login(request):
    """Render the login page (GET) or processes a login form submission
    (POST). A successful login redirects to the URL specified by.

    ?next=... or, failing that, the home page.
    """
    d = {"menu_item": "ui_null.null"}
    if request.method == "GET":
        if "next" in request.GET:
            try:
                # m = django.urls.resolvers.resolve(request.GET["next"])
                m = django.urls.resolve(request.GET["next"])
                if m.app_name == "admin":
                    django.contrib.messages.error(
                        request,
                        _("You must be logged in as an administrator to view this page."),
                    )
            except django.urls.resolvers.Resolver404:
                pass
            d["next"] = request.GET["next"]
        else:
            d["next"] = django.urls.reverse("ui_home.index")
        # noinspection PyUnresolvedReferences
        return impl.ui_common.render(request, "account/login", d)
    elif request.method == "POST":
        if (
            "username" not in request.POST
            or "password" not in request.POST
            or "next" not in request.POST
        ):
            return impl.ui_common.badRequest(request)
        d.update(impl.ui_common.extract(request.POST, ["username", "password", "next"]))
        user = impl.userauth.authenticate(d["username"], d["password"], request)
        if type(user) is str:
            django.contrib.messages.error(request, impl.ui_common.formatError(user))
            # noinspection PyUnresolvedReferences
            return impl.ui_common.render(request, "account/login", d)
        if user is not None:
            # 'extra_tags' used for recording a Google Analytics event
            django.contrib.messages.add_message(
                request,
                django.contrib.messages.SUCCESS,
                _("Login successful."),
                extra_tags='Accounts Submit Login',
            )
            if django.utils.http.url_has_allowed_host_and_scheme(url=d["next"], allowed_hosts=[request.get_host()]):
                return django.shortcuts.redirect(d["next"])
            else:
                return django.shortcuts.redirect("ui_home.index")
        else:
            django.contrib.messages.error(request, _("Login failed."))
            # noinspection PyUnresolvedReferences
            return impl.ui_common.render(request, "account/login", d)
    else:
        return impl.ui_common.methodNotAllowed(request)


def logout(request):
    """Log the user out and redirects to the home page."""
    _d = {'menu_item': 'ui_null.null'}
    if request.method != "GET":
        return impl.ui_common.methodNotAllowed(request)
    request.session.flush()
    django.contrib.messages.success(request, _("You have been logged out."))
    return django.shortcuts.redirect("ui_home.index")


@impl.ui_common.user_login_required
def edit(request):
    """Edit account information form."""
    d = {'menu_item': 'ui_account.edit'}
    user = impl.userauth.getUser(request)
    d["username"] = user.username

    proxies_orig = [u.username for u in user.proxies.all().order_by("username")]
    pusers = {
        u.username: u.displayName
        for u in allUsersInRealm(user)
        if u.displayName != user.displayName
    }
    d['proxy_users_choose'] = sorted(list(pusers.items()), key=operator.itemgetter(0))
    if request.method == "GET":
        d['primaryContactName'] = user.primaryContactName
        d['primaryContactEmail'] = user.primaryContactEmail
        d['primaryContactPhone'] = user.primaryContactPhone
        d['secondaryContactName'] = user.secondaryContactName
        d['secondaryContactEmail'] = user.secondaryContactEmail
        d['secondaryContactPhone'] = user.secondaryContactPhone
        d['accountDisplayName'] = user.displayName
        d['accountEmail'] = user.accountEmail
        d['crossrefEmail'] = user.crossrefEmail
        proxy_for_list = user.proxy_for.all().order_by("username")
        d['proxy_for'] = (
            "<br/> ".join(
                "[" + u.username + "]&nbsp;&nbsp;&nbsp;" + u.displayName for u in proxy_for_list
            )
            if proxy_for_list
            else "None"
        )
        d['proxies_default'] = proxies_default
        d['proxy_users_picked_list'] = json.dumps(proxies_orig)
        d['proxy_users_picked'] = ', '.join(proxies_orig if proxies_orig else [proxies_default])
        d['form'] = impl.form_objects.UserForm(d, user=user, username=d['username'], pw_reqd=False)
    elif request.method == "POST":
        d['form'] = impl.form_objects.UserForm(
            request.POST, initial=d, user=user, username=d['username'], pw_reqd=False
        )
        basic_info_changed = False
        newProxies = None
        if d['form'].is_valid():
            if d['form'].has_changed():
                basic_info_changed = any(
                    ch in d['form'].changed_data for ch in ACCOUNT_FIELDS_EDITABLE
                )
                if request.POST['proxy_users_picked'] not in ["", proxies_default]:
                    newProxies = _getNewProxies(
                        user,
                        proxies_orig,
                        [x.strip() for x in request.POST['proxy_users_picked'].split(",")],
                    )
            _update_edit_user(request, user, newProxies, basic_info_changed)
        else:  # Form did not validate
            if '__all__' in d['form'].errors:
                # non_form_error, probably due to all fields being empty
                all_errors = ''
                errors = d['form'].errors['__all__']
                for e in errors:
                    all_errors += e
                django.contrib.messages.error(
                    request, _("Change(s) could not be made. ") + all_errors
                )
            else:
                err = _(
                    "Change(s) could not be made. Please check the highlighted field(s) below for details."
                )
                django.contrib.messages.error(request, err)
    else:
        return impl.ui_common.methodNotAllowed(request)
    # noinspection PyUnresolvedReferences
    return impl.ui_common.render(request, "account/edit", d)


def allUsersInRealm(user):
    realmusers = []
    for group in user.realm.groups.all():
        realmusers.extend(group.users.all())
    return sorted(realmusers, key=lambda k: k.username)


def _getNewProxies(_user, orig, picked):
    """Compare two lists of usernames

    Returns list of newly picked users, as User objects. Not removing
    any users at the moment.
    """
    r = []
    p = list(set(picked) - set(orig))
    if p:
        for proxyname in p:
            r.extend([ezidapp.models.util.getUserByUsername(proxyname)])
    return r


def _update_edit_user(request, user, new_proxies_selected, basic_info_changed):
    """method to update the user editing his/her information."""
    d = request.POST
    try:
        with django.db.transaction.atomic():
            user.primaryContactName = d["primaryContactName"]
            user.primaryContactEmail = d["primaryContactEmail"]
            user.primaryContactPhone = d["primaryContactPhone"]
            user.secondaryContactName = d["secondaryContactName"]
            user.secondaryContactEmail = d["secondaryContactEmail"]
            user.secondaryContactPhone = d["secondaryContactPhone"]
            user.displayName = d["accountDisplayName"]
            user.accountEmail = d["accountEmail"]
            # user.proxies.clear()
            for p_user in [p_user.strip() for p_user in d["proxy_users_picked"].split(",")]:
                if p_user not in ["", proxies_default]:
                    user.proxies.add(ezidapp.models.util.getUserByUsername(p_user))
            if d["pwcurrent"].strip() != "":
                user.setPassword(d["pwnew"].strip())
            user.full_clean(validate_unique=False)
            user.save()
            ezidapp.admin.scheduleUserChangePostCommitActions(user)
    except django.core.validators.ValidationError as e:
        django.contrib.messages.error(request, str(e))
    else:
        if new_proxies_selected:
            _sendUserEmail(request, user, new_proxies_selected)
            for new_proxy in new_proxies_selected:
                _sendProxyEmail(request, new_proxy, user)
        if basic_info_changed:
            django.contrib.messages.success(request, _("Your information has been updated."))
        if d['pwcurrent'].strip() != '' and d['pwnew'].strip() != '':
            django.contrib.messages.success(request, _("Your password has been updated."))


def _sendEmail(request, user:ezidapp.models.user.User, subject:str, message:str, to_address:str=None):
    to_address = to_address or user.accountEmail
    to_full_address = user.primaryContactName + "<" + to_address + ">"
    log.info(f'Sending email:\nTo: {to_full_address}\nSubject: {subject}\n{message}')
    try:
        django.core.mail.send_mail(
            subject,
            message,
            django.conf.settings.SERVER_EMAIL,
            [to_address],
            fail_silently=True,
        )
    except Exception as e:
        django.contrib.messages.error(
            request,
            _("Error sending email to {username}: {errormessage}").format(
                {'username': to_full_address, 'errormessage': str(e)}
            ),
        )


def _sendProxyEmail(request, p_user, user):
    m = (
        _("Dear")
        + " {},\n\n"
        + _("You have been added as a proxy user to the identifiers owned by the following ")
        + _("primary user")
        + ":\n\n"
        + "   "
        + _("User")
        + ": {}\n"
        + "   "
        + _("Username")
        + ": {}\n"
        + "   "
        + _("Account")
        + ": {}\n"
        + "   "
        + _("Account Email")
        + ": {}\n\n"
        + _("As a proxy user, you can create and modify identifiers owned by the primary user")
        + ". "
        + _("If you need more information about proxy ownership of EZID identifiers, ")
        + _("please don't hesitate to contact us")
        + ": https://ezid.cdlib.org/contact\n\n"
        + _("Best,\nEZID Team\n\n\nThis is an automated email. Please do not reply.\n")
    ).format(
        p_user.primaryContactName,
        user.primaryContactName,
        user.username,
        user.displayName,
        user.accountEmail,
    )
    _sendEmail(request, p_user, _("You've Been Added as an EZID Proxy User"), m)


def _sendUserEmail(request, user, new_proxies):
    plural = True if len(new_proxies) > 1 else False
    intro = _("These proxy users have been") if plural else _("This proxy user has been")
    p_list = ""
    for p in new_proxies:
        p_list += (
            "*** EZID "
            + _("User")
            + ": "
            + p.username
            + "   |   "
            + _("Name")
            + ": "
            + p.displayName
            + "  ***\n"
        )
    m = (
        _("Dear")
        + " {},\n\n"
        + _("Thank you for using EZID to easily create and manage your identifiers.")
        + " {} "
        + _("successfully added to your account")
        + ":\n\n{}\n\n"
        + _("To manage your account's proxy users, please log into EZID and go to")
        + " ezid.cdlib.org/account/edit.\n\n"
        + _("Best,\nEZID Team\n\n\nThis is an automated email. Please do not reply.\n")
    ).format(user.primaryContactName, intro, p_list)
    subj = (_("New EZID Proxy User{} Added")).format("s" if plural else "")
    _sendEmail(request, user, subj, m)


def pwreset(request, pwrr=None):
    """Handle all GET and POST interactions related to password resets."""
    if pwrr:  # Change password here after receiving email
        d = {'menu_item': 'ui_null.null'}
        r = decodePasswordResetRequest(pwrr)
        if not r:
            django.contrib.messages.error(request, _("Invalid password reset request."))
            return django.http.HttpResponseRedirect("/")
        username, t = r
        if int(time.time()) - t >= 24 * 60 * 60:
            django.contrib.messages.error(request, _("Password reset request has expired."))
            return django.http.HttpResponseRedirect("/")
        d['pwrr'] = pwrr
        if request.method == "GET":
            d['username'] = username
            d['form'] = impl.form_objects.BasePasswordForm(None, username=username, pw_reqd=True)
        elif request.method == "POST":
            if "pwnew" not in request.POST or "pwconfirm" not in request.POST:
                return impl.ui_common.badRequest(request)
            password = request.POST["pwnew"]
            d['form'] = impl.form_objects.BasePasswordForm(
                request.POST, username=username, pw_reqd=True
            )
            if not d['form'].is_valid():
                err = _(
                    "Changes could not be made. Please check the highlighted field(s) below for details."
                )
                django.contrib.messages.error(request, err)
            else:
                user = ezidapp.models.util.getUserByUsername(username)
                if user is None or user.isAnonymous:
                    django.contrib.messages.error(request, _("No such user."))
                    # noinspection PyUnresolvedReferences
                    return impl.ui_common.render(request, "account/pwreset2", d)
                with django.db.transaction.atomic():
                    user.setPassword(password)
                    user.save()
                    ezidapp.admin.scheduleUserChangePostCommitActions(user)
                django.contrib.messages.success(request, _("Password changed."))
                return django.http.HttpResponseRedirect("/")
        else:
            return impl.ui_common.methodNotAllowed(request)
        # noinspection PyUnresolvedReferences
        return impl.ui_common.render(request, "account/pwreset2", d)
    else:
        # First step: enter your username and email to get sent an email containing link for password change
        d = {'menu_item': 'ui_null.null'}
        if request.method == "GET":
            d['form'] = impl.form_objects.PwResetLandingForm()
            # noinspection PyUnresolvedReferences
            return impl.ui_common.render(request, "account/pwreset1", d)
        elif request.method == "POST":
            P = request.POST
            if "username" not in P or "email" not in P:
                return impl.ui_common.badRequest(request)
            username = P["username"].strip()
            email = P["email"].strip()
            d['form'] = impl.form_objects.PwResetLandingForm(P)
            if not d['form'].is_valid():
                # noinspection PyUnresolvedReferences
                return impl.ui_common.render(request, "account/pwreset1", d)
            else:
                r = sendPasswordResetEmail(request, username, email)
                if type(r) in (str, str):
                    django.contrib.messages.error(request, r)
                    # noinspection PyUnresolvedReferences
                    return impl.ui_common.render(request, "account/pwreset1", d)
                else:
                    django.contrib.messages.success(request, _("Email sent."))
                    return django.http.HttpResponseRedirect("/")
        else:
            return impl.ui_common.methodNotAllowed(request)


def sendPasswordResetEmail(request, username:str, emailAddress:str):
    """Send an email containing a password reset request link

    Returns None on success or a string message on error.
    """
    user = ezidapp.models.util.getUserByUsername(username)
    if user is None or user.isAnonymous:
        return _("No such user.")
    if emailAddress not in [
        user.accountEmail,
        user.primaryContactEmail,
        user.secondaryContactEmail,
    ]:
        return _("Email address does not match any address registered for username.")
    t = int(time.time())
    hash = hashlib.sha1(
        f"{username}|{t:d}|{django.conf.settings.SECRET_KEY}".encode('utf-8')
    ).hexdigest()[::4]
    link = "{}/account/pwreset/{},{},{}".format(
        django.conf.settings.EZID_BASE_URL,
        urllib.parse.quote(username),
        t,
        hash,
    )
    message = (
        _("You have requested to reset your EZID password")
        + ".\n"
        + _("Click the link below to complete the process")
        + ":\n\n"
        + link
        + "\n\n"
        + _("Please do not reply to this email")
        + ".\n"
    )
    _sendEmail(request, user, _("EZID password reset request"), message, emailAddress)


def decodePasswordResetRequest(request):
    """Decode a password reset request, returning a tuple (username,
    timestamp) on success or None on error."""
    m = re.match("/([^ ,]+),(\\d+),([\\da-f]+)$", request)
    if not m:
        return None
    username = m.group(1)
    t = m.group(2)
    hash = m.group(3)
    if (
        hashlib.sha1(
            f"{username}|{t}|{django.conf.settings.SECRET_KEY}".encode('utf-8')
        ).hexdigest()[::4]
        != hash
    ):
        return None
    return username, int(t)
