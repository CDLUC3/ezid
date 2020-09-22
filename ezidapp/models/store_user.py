# =============================================================================
#
# EZID :: ezidapp/models/store_user.py
#
# Database model for users in the store database.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2016, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.contrib.auth.hashers
import django.contrib.auth.models
import django.core.validators
import django.db.models
import django.db.transaction

import shoulder
import store_group
import store_realm
import user
import validation

# Deferred imports...
"""
import config
import ezidapp.admin
"""


class StoreUser(user.User):

    # Inherited foreign key declarations...
    group = django.db.models.ForeignKey(
        store_group.StoreGroup, on_delete=django.db.models.PROTECT
    )
    realm = django.db.models.ForeignKey(
        store_realm.StoreRealm, on_delete=django.db.models.PROTECT
    )

    displayName = django.db.models.CharField(
        "display name", max_length=255, validators=[validation.nonEmpty]
    )
    # The user's display name, e.g., "Brown University Library", which
    # is displayed in the UI wherever the username is.  Editable by the
    # user.

    accountEmail = django.db.models.EmailField(
        "account email",
        max_length=255,
        help_text="The email address to which account-related notifications "
        + "are sent other than Crossref notifications.",
    )
    # Editable by the user.

    primaryContactName = django.db.models.CharField(
        "name", max_length=255, validators=[validation.nonEmpty]
    )
    primaryContactEmail = django.db.models.EmailField("email", max_length=255)
    primaryContactPhone = django.db.models.CharField(
        "phone", max_length=255, validators=[validation.nonEmpty]
    )
    # Primary contact info, which is required.  Editable by the user.

    secondaryContactName = django.db.models.CharField(
        "name", max_length=255, blank=True
    )
    secondaryContactEmail = django.db.models.EmailField(
        "email", max_length=255, blank=True
    )
    secondaryContactPhone = django.db.models.CharField(
        "phone", max_length=255, blank=True
    )
    # Secondary contact info, which is optional.  Editable by the user.

    inheritGroupShoulders = django.db.models.BooleanField(
        "inherit group shoulders",
        default=False,
        help_text="If checked, the user has access to all group "
        + "shoulders; if not checked, the user has access only to the shoulders "
        + "explicitly selected below.",
    )
    # If True, the user may use any of the group's shoulders; if False,
    # shoulders visible to the user are limited to those explicitly
    # listed in 'shoulders'.

    shoulders = django.db.models.ManyToManyField(shoulder.Shoulder, blank=True)
    # The shoulders to which the user has access.  If
    # inheritGroupShoulders is True, the set matches the group's set; if
    # inheritGroupShoulders if False, the user's set may be a proper
    # subset of the group's set.  Test shoulders are not included in
    # this relation.

    crossrefEnabled = django.db.models.BooleanField("Crossref enabled", default=False)
    # Deprecated and not used at present.  (Former usage:
    # If the user's group is Crossref-enabled, determines if the user
    # may register identifiers with Crossref; otherwise, False.  Note
    # that Crossref registration requires the enablement of both the
    # user and the shoulder.)

    crossrefEmail = django.db.models.EmailField(
        "Crossref email", max_length=255, blank=True
    )
    # If the user is Crossref-enabled, the optional email address to
    # which Crossref notifications are sent; otherwise, empty.  If there
    # is no email address, notifications are simply not sent.

    proxies = django.db.models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        help_text="A proxy is another user that may act on behalf of this user.",
    )
    # Other users that may act as a proxy for this user.  Editable by
    # the user.  Self-referential proxies are disallowed.  Privileged
    # users (group and realm administrators, superusers) are not allowed
    # to have proxies.

    @property
    def proxy_for(self):
        # Returns a Django related manager for the set of users this user
        # is a proxy for.
        return self.storeuser_set

    isGroupAdministrator = django.db.models.BooleanField(
        "group administrator", default=False
    )
    # True if the user is an administrator of its group.  A group
    # administrator may act on behalf of any user in the group (i.e., is
    # effectively a proxy for every group member); may perform
    # group-level operations; and may change identifier ownership within
    # the group.

    isRealmAdministrator = django.db.models.BooleanField(
        "realm administrator", default=False
    )
    # True if the user is an administrator of its realm.  A realm
    # administrator is effectively an administrator of every group in
    # the realm, and may change identifier ownership within the realm.
    # A realm administrator has no special privileges regarding
    # shoulders, however.

    isSuperuser = django.db.models.BooleanField("superuser", default=False)

    @property
    def isPrivileged(self):
        return (
            self.isGroupAdministrator or self.isRealmAdministrator or self.isSuperuser
        )

    loginEnabled = django.db.models.BooleanField("login enabled", default=True)
    # Determines if the user may login.

    password = django.db.models.CharField("set password", max_length=128, blank=True)
    # The user's password in salted/hashed/encoded form.  Despite the
    # declaration, this field will never actually be empty.  It is
    # initially given an unusable value.  Editable by the user.

    notes = django.db.models.TextField(blank=True)
    # Any additional notes.

    def clean(self):
        super(StoreUser, self).clean()
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
        # Because the Django admin app performs many-to-many operations
        # only after creating or updating objects, sadly, we can't perform
        # any validations related to shoulders or proxies here.
        # Addendum: moreover, because users are displayed inline in group
        # change pages, they get validated along with groups, before
        # StoreGroupAdmin.save_model is called.  Therefore we can't check
        # group-user Crossref-enabled consistency here.

    def setPassword(self, password):
        # Sets the user's password; 'password' should be a bare password.
        # Caution: this method sets the password in the object, but does
        # not save the object to the database.  However, if there is a
        # corresponding user in the Django auth app, that user's password
        # is both set and saved.  Thus calls to this method should
        # generally be wrapped in a transaction.
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
        """Returns True if the supplied password matches the user's."""
        logger.debug(
            'Authenticating StoreUser. displayName="{}"'.format(self.displayName)
        )

        if not self.loginEnabled:
            logger.debug('Auth denied. loginEnabled="{}"'.format(self.loginEnabled))
            return False

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
            except:
                pass

        return True

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    def __unicode__(self):
        return "%s (%s)" % (self.username, self.displayName)

    isAnonymous = False
    # See below.


# The following caches are only added to or replaced entirely;
# existing entries are never modified.  Thus, with appropriate coding
# below, they are threadsafe without needing locking.

_caches = None  # (pidCache, usernameCache, idCache)


def clearCaches():
    global _caches
    _caches = None


def _databaseQuery():
    return StoreUser.objects.select_related("group", "realm").prefetch_related(
        "shoulders", "proxies"
    )


def _getCaches():
    global _caches
    caches = _caches
    if caches == None:
        pidCache = dict((u.pid, u) for u in _databaseQuery().all())
        usernameCache = dict((u.username, u) for u in pidCache.values())
        idCache = dict((u.id, u) for u in pidCache.values())
        caches = (pidCache, usernameCache, idCache)
        _caches = caches
    return caches


def getByPid(pid):
    # Returns the user identified by persistent identifier 'pid', or
    # None if there is no such user.  AnonymousUser is returned in
    # response to "anonymous".
    if pid == "anonymous":
        return AnonymousUser
    pidCache, usernameCache, idCache = _getCaches()
    if pid not in pidCache:
        try:
            u = _databaseQuery().get(pid=pid)
        except StoreUser.DoesNotExist:
            return None
        pidCache[pid] = u
        usernameCache[u.username] = u
        idCache[u.id] = u
    return pidCache[pid]


def getByUsername(username):
    # Returns the user identified by local name 'username', or None if
    # there is no such user.  AnonymousUser is returned in response to
    # "anonymous".
    if username == "anonymous":
        return AnonymousUser
    pidCache, usernameCache, idCache = _getCaches()
    if username not in usernameCache:
        try:
            u = _databaseQuery().get(username=username)
        except StoreUser.DoesNotExist:
            return None
        pidCache[u.pid] = u
        usernameCache[username] = u
        idCache[u.id] = u
    return usernameCache[username]


def getById(id):
    # Returns the user identified by internal identifier 'id', or None
    # if there is no such user.
    pidCache, usernameCache, idCache = _getCaches()
    if id not in idCache:
        try:
            u = _databaseQuery().get(id=id)
        except StoreUser.DoesNotExist:
            return None
        pidCache[u.pid] = u
        usernameCache[u.username] = u
        idCache[id] = u
    return idCache[id]


def getAdminUser():
    # Returns the EZID administrator user.
    import config

    return getByUsername(config.get("auth.admin_username"))


class AnonymousUser(object):
    # A class to represent an anonymous user.  Note that this class can
    # be used directly--- an object need not be instantiated.
    pid = "anonymous"
    username = "anonymous"
    group = store_group.AnonymousGroup
    realm = store_realm.AnonymousRealm

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
