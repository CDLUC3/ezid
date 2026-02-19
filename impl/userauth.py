#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""User authentication
"""

import base64
import hashlib
import logging

import django.conf
import django.contrib.auth
import django.contrib.auth.hashers
import django.contrib.auth.models
import django.utils.encoding

import ezidapp.models.user
import ezidapp.models.util
import impl.log
import impl.util

SESSION_KEY = "ezidAuthenticatedUser"


logger = logging.getLogger(__name__)


def authenticate(username, password, request=None, coAuthenticate=True):
    """Authenticate a username and password

    Returns a User object if the authentication is successful, None if
    unsuccessful, or a string error message if an error occurs.

    This implements EZID's custom authentication, and in this context, the 'admin'
    user authenticates like regular users.

    If 'request' is not None, the appropriate variables are added to the request
    session.

    If 'request' is not None and coAuthenticate is True, and if the user is an
    administrative user, the user is authenticated with the Django admin app as well.

    Easter egg: if the username has the form "@user" and the EZID administrator password
    is given, and if username "user" exists, then a User object for "user" is
    returned (even if logins are not enabled for the user).
    """
    logger.debug('Authenticating user. username="{}"'.format(username))
    if username.startswith("@"):
        username = username[1:]
        sudo = True
        logger.debug('User is authenticating as an administrator')
    else:
        sudo = False
        logger.debug('User is authenticating as a regular, non-privileged user')

    username = username.strip()
    if username == "":
        logger.debug(
            'Auth failed due to missing username. username="{}"'.format(username)
        )
        return "error: bad request - username required"

    password = password.strip()
    if password == "":
        logger.debug(
            'Auth failed due to missing password. username="{}"'.format(username)
        )
        return "error: bad request - password required"

    # noinspection PyUnresolvedReferences
    user = ezidapp.models.util.getUserByUsername(username)
    logger.debug('Username resolved. user="{}"'.format(user))

    if user is None or user.isAnonymous:
        # noinspection PyUnresolvedReferences
        logger.debug(
            'Auth failed due unknown or anonymous user. '
            'user="{}" user.isAnonymous={}'.format(
                user, None if not user else user.isAnonymous
            )
        )
        return None

    if (sudo and ezidapp.models.util.getAdminUser().authenticate(password)) or (
        not sudo and user.authenticate(password)
    ):
        logger.debug('Auth successful. user="{}" sudo="{}"'.format(user, sudo))

        if request is not None:
            logger.debug('Auth in active request')

            request.session[SESSION_KEY] = user.id
            # Add session variables to support the Django admin interface.
            if (
                coAuthenticate
                and not sudo
                and django.contrib.auth.models.User.objects.filter(
                    username=username
                ).exists()
            ):
                authUser = django.contrib.auth.authenticate(
                    username=username, password=password
                )
                if authUser is not None:
                    django.contrib.auth.login(request, authUser)
                else:
                    impl.log.otherError(
                        "userauth.authenticate",
                        Exception(
                            "administrator password mismatch; run "
                            + "'./manage.py diag-update-admin' to correct"
                        ),
                    )
        else:
            logger.debug('Auth without an active request')
        return user
    else:
        logger.debug('Auth failed. username="{}" sudo="{}"'.format(username, sudo))
        return None


def getUser(request, returnAnonymous=False):
    """If the session is authenticated, returns a User object for the
    authenticated user; otherwise, returns None.

    If returnAnonymous is True, AnonymousUser is returned instead of
    None.
    """
    if SESSION_KEY in request.session:
        user = ezidapp.models.util.getUserById(request.session[SESSION_KEY])
        if user is not None and user.loginEnabled:
            return user
        else:
            return ezidapp.models.user.AnonymousUser if returnAnonymous else None
    else:
        return ezidapp.models.user.AnonymousUser if returnAnonymous else None


def authenticateRequest(request, storeSessionCookie=False):
    """Authenticate an API request

    Returns a User object if the authentication is successful, None
    if unsuccessful, or a string error message if an error occurs.
    """
    if SESSION_KEY in request.session:
        user = ezidapp.models.util.getUserById(request.session[SESSION_KEY])
        if user is not None and user.loginEnabled:
            return user
        else:
            return None
    elif "HTTP_AUTHORIZATION" in request.META:
        try:
            u, p = impl.util.parse_basic_auth(request.META["HTTP_AUTHORIZATION"])
        except ValueError:
            return "error: bad request - malformed Authorization header"
        except Exception as e:
            return "error: unable to parse basic_auth request"
        return authenticate(
            u,
            p,
            request=(request if storeSessionCookie else None),
            coAuthenticate=False,
        )
    else:
        return None

