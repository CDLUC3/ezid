import logging

import django.apps
import django.conf

from ezidapp.models.group import AnonymousGroup, StoreGroup

logger = logging.getLogger(__name__)


def _databaseQueryStoreUser():
    store_user_model = django.apps.apps.get_model('ezidapp', 'StoreUser')
    try:
        return store_user_model.objects.select_related("group", "realm").prefetch_related("shoulders", "proxies")
    except store_user_model.DoesNotExist:
        return None

def getUserById(id_str):
    # Returns the user identified by internal identifier 'id', or None
    # if there is no such user.
    # pidCache, usernameCache, idCache = _getCaches()
    # if id_str not in idCache:
    return _databaseQueryStoreUser().get(id=id_str)


def getUserByPid(pid):
    # Returns the user identified by persistent identifier 'pid', or
    # None if there is no such user.  AnonymousUser is returned in
    # response to "anonymous".
    if pid == "anonymous":
        anon_user_model = django.apps.apps.get_model('ezidapp', 'AnonymousUser')
        return anon_user_model
    return _databaseQueryStoreUser().get(pid=pid)


def getUserByUsername(username):
    # Returns the user identified by local name 'username', or None if
    # there is no such user.  AnonymousUser is returned in response to
    # "anonymous".
    if username == "anonymous":
        return AnonymousUser
    return _databaseQueryStoreUser().get(username=username)


def getAdminUser():
    # Returns the EZID administrator user.
    return getUserByUsername(django.conf.settings.ADMIN_USERNAME)


def getProfileByLabel(label):
    # Returns the profile having the given label.  If there's no such
    # profile, a new profile is created and inserted in the database.
    store_profile_model = django.apps.apps.get_model('ezidapp', 'StoreProfile')
    p, is_created = store_profile_model.objects.get_or_create(label=label)
    if is_created:
        p.full_clean(validate_unique=False)
        p.save()
    return p



class AnonymousUser(object):
    # A class to represent an anonymous user.  Note that this class can
    # be used directly--- an object need not be instantiated.
    pid = "anonymous"
    username = "anonymous"

    # group = ezidapp.models.group.AnonymousGroup
    # anonymous_group_model = django.apps.apps.get_model('ezidapp', 'AnonymousGroup')
    # realm = django.apps.apps.get_model('ezidapp', 'AnonymousRealm')

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


# Group

def _databaseQueryGroup():
    store_group_model = django.apps.apps.get_model('ezidapp', 'StoreGroup')
    try:
        return store_group_model.objects.select_related("group", "realm").prefetch_related("shoulders", "proxies")
    except store_group_model.DoesNotExist:
        return None

# TODO
def _databaseQueryStoreGroup():
    return StoreGroup.objects.select_related("realm").prefetch_related("shoulders")

def getGroupByPid(pid):
    # Returns the group identified by persistent identifier 'pid', or
    # None if there is no such group.  AnonymousGroup is returned in
    # response to "anonymous".
    if pid == "anonymous":
        return AnonymousGroup
    return _databaseQueryGroup().get(pid=pid)


def getGroupByGroupname(groupname):
    # Returns the group identified by local name 'groupname', or None if
    # there is no such group.  AnonymousGroup is returned in response to
    # "anonymous".
    if groupname == "anonymous":
        return AnonymousGroup
    return _databaseQueryGroup().get(groupname=groupname)


# Profile

def _databaseQueryProfile():
    return StoreGroup.objects.select_related("realm").prefetch_related("shoulders")

def getProfileById(id_str):
    # Returns the group identified by internal identifier 'id', or None
    # if there is no such group.
    return _databaseQueryProfile().get(id=id_str)


# Datacenter

def _databaseQueryDatacenter():
    datacenter_model = django.apps.apps.get_model('ezidapp', 'StoreDatacenter')
    try:
        return datacenter_model.objects
    except datacenter_model.DoesNotExist:
        pass


def getDatacenterById(id_str):
    # Returns the datacenter identified by internal identifier 'id'.
    return django.apps.apps.get_model('ezidapp', 'StoreDatacenter').get(id=id_str)


def getDatacenterBySymbol(symbol):
    # Returns the datacenter having the given symbol.
    return django.apps.apps.get_model('ezidapp', 'StoreDatacenter').get(symbol=symbol)
