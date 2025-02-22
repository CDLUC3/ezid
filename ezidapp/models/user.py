#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Object Relational Mapper (ORM) models for users
"""

import logging
import re

import django.apps
import django.conf
import django.contrib.auth.hashers
import django.contrib.auth.models
import django.core.exceptions
import django.core.validators
import django.db.models
import django.db.models
import django.db.transaction

import ezidapp.models.shoulder
import ezidapp.models.validation
import ezidapp.models.group
import ezidapp.models.realm
import impl.log

import impl.log as log
import impl.nog_sql.ezid_minter
import impl.util

logger = logging.getLogger(__name__)


class User(django.db.models.Model):
    """An EZID user (login account)
    """
    class Meta:
        # abstract = True
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return f"{self.username} ({self.displayName})"

    def clean(self):
        # Because the Django admin app performs many-to-many operations only after creating or
        # updating objects, sadly, we can't perform any validations related to shoulders or proxies
        # here.
        #
        # Moreover, because users are displayed inline in group change pages, they get validated
        # along with groups, before GroupAdmin.save_model is called. Therefore we can't check
        # group-user Crossref-enabled consistency here.
        if self.username == "anonymous":
            raise django.core.validators.ValidationError(
                {"username": "The name 'anonymous' is reserved."}
            )
        self.displayName = self.displayName.strip()
        self.primaryContactName = self.primaryContactName.strip()
        self.primaryContactPhone = self.primaryContactPhone.strip()
        self.secondaryContactName = self.secondaryContactName.strip()
        self.secondaryContactPhone = self.secondaryContactPhone.strip()
        self.notes = self.notes.strip()
        if self.password == "":
            self.setPassword(None)


        # The following two statements are here just to support the Django
        # admin app, which has its own rules about how model objects are
        # constructed. If no group has been assigned, we can return
        # immediately because a validation error will already have been
        # triggered.
        if not hasattr(self, "group"):
            return
        if not hasattr(self, "realm"):
            # noinspection PyUnresolvedReferences
            self.realm = self.group.realm
        # noinspection PyUnresolvedReferences
        if self.realm != self.group.realm:
            raise django.core.exceptions.ValidationError(
                "User's realm does not match user's group's realm."
            )
        if self.pid == "":
            try:
                s = ezidapp.models.shoulder.getAgentShoulder()
                assert s.isArk, "Agent shoulder type must be ARK"
                self.pid = "{}{}".format(s.prefix, impl.nog_sql.ezid_minter.mint_id(s))
            except Exception as e:
                impl.log.otherError("user.User.clean", e)
                raise


    def setPassword(self, password):
        """Set the user's password

        'password' should be a bare password.

        Caution: this method sets the password in the object, but does
        not save the object to the database. However, if there is a
        corresponding user in the Django auth app, that user's password
        is both set and saved. Thus calls to this method should
        generally be wrapped in a transaction.

        Django's standard password hasher is used. Currently, this is PBKDF
        (password based key derivation function), with 20,000 iterations.

        The password is salted, so setting the same password multiple times will yield
        a different hash each time.
        """
        logger.debug(
            'Setting password for user. displayName="{}"'.format(self.displayName)
        )
        self.password = django.contrib.auth.hashers.make_password(password)
        try:
            au = django.contrib.auth.models.User.objects.get(username=self.username)
            au.set_password(password)
            au.save()
        except django.contrib.auth.models.User.DoesNotExist:
            pass

    def authenticate(self, password):
        """Return True if the supplied password matches the user's."""
        logger.debug(
            'Authenticating User. displayName="{}"'.format(self.displayName)
        )

        if not self.loginEnabled:
            logger.debug('Auth denied. loginEnabled="{}"'.format(self.loginEnabled))
            return False

        try:
            is_valid = django.contrib.auth.hashers.check_password(
                password, self.password
            )
        except Exception as e:
            logger.error('failed')

        if not django.contrib.auth.hashers.check_password(password, self.password):
            logger.debug('Auth denied. Password check failed')
            logger.debug(
                'User\'s hashed pw: {}'.format(
                    # self.password
                    django.contrib.auth.hashers.make_password(password)
                )
            )
            try:
                user_model = django.contrib.auth.models.User.objects.get(
                    username=self.username
                )
            except django.contrib.auth.models.User.DoesNotExist:
                logger.debug('Auth record does not exist for user')
            else:
                logger.debug(
                    'Auth record exists for user and contains hashed pw: {}'.format(
                        user_model.password
                    )
                )
            return False

        logger.debug('Auth successful')

        # Upgrade older LDAP password hashes.
        if self.password.split("$")[0] == "ldap_sha1":
            import ezidapp.admin

            try:
                with django.db.transaction.atomic():
                    self.setPassword(password)
                    self.save()
                    ezidapp.admin.scheduleUserChangePostCommitActions(self)
            except Exception:
                pass

        return True

    # See below.
    isAnonymous = False

    # The user's persistent identifier, e.g., "ark:/99166/bar". Note
    # that the uniqueness requirement is actually stronger than
    # indicated here: it is expected that all agent (i.e., all user and
    # group) persistent identifiers are unique.
    pid = django.db.models.CharField(
        max_length=impl.util.maxIdentifierLength,
        unique=True,
        validators=[ezidapp.models.validation.agentPid],
    )

    # The user's username, e.g., "dryad".
    username = django.db.models.CharField(
        max_length=32,
        unique=True,
        validators=[
            django.core.validators.RegexValidator(
                "^[a-z0-9]+([-_.][a-z0-9]+)*$", "Invalid username.", flags=re.I
            )
        ],
    )

    group = django.db.models.ForeignKey(
        'ezidapp.Group', on_delete=django.db.models.PROTECT
    )

    realm = django.db.models.ForeignKey(
        'ezidapp.Realm', on_delete=django.db.models.PROTECT
    )

    # The user's display name, e.g., "Brown University Library", which
    # is displayed in the UI wherever the username is. Editable by the
    # user.
    displayName = django.db.models.CharField(
        "display name", max_length=255, validators=[ezidapp.models.validation.nonEmpty]
    )

    # Editable by the user.
    accountEmail = django.db.models.EmailField(
        "account email",
        max_length=255,
        help_text="The email address to which account-related notifications "
        + "are sent other than Crossref notifications.",
    )

    # Primary contact info, which is required. Editable by the user.
    primaryContactName = django.db.models.CharField(
        "name", max_length=255, validators=[ezidapp.models.validation.nonEmpty]
    )
    primaryContactEmail = django.db.models.EmailField("email", max_length=255)
    primaryContactPhone = django.db.models.CharField(
        "phone", max_length=255, validators=[ezidapp.models.validation.nonEmpty]
    )

    # Secondary contact info, which is optional. Editable by the user.
    secondaryContactName = django.db.models.CharField(
        "name", max_length=255, blank=True
    )
    secondaryContactEmail = django.db.models.EmailField(
        "email", max_length=255, blank=True
    )
    secondaryContactPhone = django.db.models.CharField(
        "phone", max_length=255, blank=True
    )

    # If True, the user may use any of the group's shoulders; if False,
    # shoulders visible to the user are limited to those explicitly
    # listed in 'shoulders'.
    inheritGroupShoulders = django.db.models.BooleanField(
        "inherit group shoulders",
        default=False,
        help_text="If checked, the user has access to all group "
        + "shoulders; if not checked, the user has access only to the shoulders "
        + "explicitly selected below.",
    )
    shoulder_model = django.apps.apps.get_model('ezidapp', 'Shoulder')

    # The shoulders to which the user has access. If
    # inheritGroupShoulders is True, the set matches the group's set; if
    # inheritGroupShoulders if False, the user's set may be a proper
    # subset of the group's set. Test shoulders are not included in
    # this relation.
    shoulders = django.db.models.ManyToManyField(shoulder_model, blank=True)

    # Deprecated and not used at present. (Former usage:
    # If the user's group is Crossref-enabled, determines if the user
    # may register identifiers with Crossref; otherwise, False. Note
    # that Crossref registration requires the enablement of both the
    # user and the shoulder.)
    crossrefEnabled = django.db.models.BooleanField("Crossref enabled", default=False)

    # If the user is Crossref-enabled, the optional email address to
    # which Crossref notifications are sent; otherwise, empty. If there
    # is no email address, notifications are simply not sent.
    crossrefEmail = django.db.models.EmailField(
        "Crossref email", max_length=255, blank=True
    )

    # Other users that may act as a proxy for this user. Editable by
    # the user. Self-referential proxies are disallowed. Privileged
    # users (group and realm administrators, superusers) are not allowed
    # to have proxies.
    proxies = django.db.models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        help_text="A proxy is another user that may act on behalf of this user.",
    )

    @property
    def proxy_for(self):
        # Returns a Django related manager for the set of users this user
        # is a proxy for.
        return self.user_set

    # True if the user is an administrator of its group. A group
    # administrator may act on behalf of any user in the group (i.e., is
    # effectively a proxy for every group member); may perform
    # group-level operations; and may change identifier ownership within
    # the group.
    isGroupAdministrator = django.db.models.BooleanField(
        "group administrator", default=False
    )

    # True if the user is an administrator of its realm. A realm
    # administrator is effectively an administrator of every group in
    # the realm, and may change identifier ownership within the realm.
    # A realm administrator has no special privileges regarding
    # shoulders, however.
    isRealmAdministrator = django.db.models.BooleanField(
        "realm administrator", default=False
    )

    isSuperuser = django.db.models.BooleanField("superuser", default=False)

    @property
    def isPrivileged(self):
        return (
            self.isGroupAdministrator or self.isRealmAdministrator or self.isSuperuser
        )

    # Determines if the user may login.
    loginEnabled = django.db.models.BooleanField("login enabled", default=True)

    # The user's password in salted/hashed/encoded form. Despite the
    # declaration, this field will never actually be empty. It is
    # initially given an unusable value. Editable by the user.
    password = django.db.models.CharField("set password", max_length=128, blank=True)

    # Any additional notes.
    notes = django.db.models.TextField(blank=True)



# The following caches are only added to or replaced entirely;
# existing entries are never modified. Thus, with appropriate coding
# below, they are threadsafe without needing locking.

# _caches = None  # (pidCache, usernameCache, idCache)


# def clearCaches():
#     global _caches
#     _caches = None


# def _getCaches():
#     global _caches
#     caches = _caches
#     if caches is None:
#         pidCache = dict((u.pid, u) for u in _databaseQuery().all())
#         usernameCache = dict((u.username, u) for u in list(pidCache.values()))
#         idCache = dict((u.id, u) for u in list(pidCache.values()))
#         caches = (pidCache, usernameCache, idCache)
#         _caches = caches
#     return caches


class AnonymousUser(object):
    """An anonymous user

    This class can be used directly. An object need not be instantiated.
    """
    pid = "anonymous"
    username = "anonymous"

    # anonymous_group_model = django.apps.apps.get_model('ezidapp', 'AnonymousGroup')
    group = ezidapp.models.group.AnonymousGroup
    #realm = django.apps.apps.get_model('ezidapp', 'AnonymousRealm')
    realm = ezidapp.models.realm.AnonymousRealm

    class inner(object):
        def all(self):
            return []

    shoulders = inner()
    crossrefEnabled = False
    crossrefEmail = ""
    proxies = inner()
    proxy_for = inner()
    isGroupAdministrator = False
    isRealmAdministrator = False
    isSuperuser = False
    isPrivileged = False
    loginEnabled = False
    isAnonymous = True

    @staticmethod
    def authenticate(password):
        logger.debug('User is anonymous. Auth denied')
        return False
