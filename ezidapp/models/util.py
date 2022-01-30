#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import logging

import django.apps
import django.conf

import ezidapp.models.user
import ezidapp.models.group

logger = logging.getLogger(__name__)


def _getUserPrefetch(**get_args):
    user_model = django.apps.apps.get_model('ezidapp', 'User')
    try:
        return (
            user_model.objects.select_related("group", "realm")
            .prefetch_related("shoulders", "proxies")
            .get(**get_args)
        )
    except user_model.DoesNotExist:
        return None


def getUserById(id_str):
    # Returns the user identified by internal identifier 'id', or None
    # if there is no such user.
    return _getUserPrefetch(id=id_str)


def getUserByPid(pid):
    # Returns the user identified by persistent identifier 'pid', or
    # None if there is no such user. AnonymousUser is returned in
    # response to "anonymous".
    if pid == "anonymous":
        return ezidapp.models.user.AnonymousUser
        # anon_user_model = django.apps.apps.get_model('ezidapp', 'AnonymousUser')
        # return anon_user_model
    return _getUserPrefetch(pid=pid)


def getUserByUsername(username):
    # Returns the user identified by local name 'username', or None if
    # there is no such user. AnonymousUser is returned in response to
    # "anonymous".
    if username == "anonymous":
        return ezidapp.models.user.AnonymousUser
    return _getUserPrefetch(username=username)


def getAdminUser():
    # Returns the EZID administrator user.
    return getUserByUsername(django.conf.settings.ADMIN_USERNAME)


def getProfileByLabel(label):
    # Returns the profile having the given label. If there's no such
    # profile, a new profile is created and inserted in the database.
    profile_model = django.apps.apps.get_model('ezidapp', 'Profile')
    p, is_created = profile_model.objects.get_or_create(label=label)
    if is_created:
        p.full_clean(validate_unique=False)
        p.save()
    return p


# Group


def _getGroupPrefetch(**get_kwargs):
    group_model = django.apps.apps.get_model('ezidapp', 'Group')
    try:
        return (
            group_model.objects.select_related("realm")
            .prefetch_related("shoulders")
            .get(**get_kwargs)
        )
        # return store_group_model.objects.select_related("group", "realm").prefetch_related("shoulders", "proxies")
    except group_model.DoesNotExist:
        return None


def getGroupByPid(pid):
    # Returns the group identified by persistent identifier 'pid', or
    # None if there is no such group. AnonymousGroup is returned in
    # response to "anonymous".
    if pid == "anonymous":
        return ezidapp.models.group.AnonymousGroup
    return _getGroupPrefetch(pid=pid)


def getGroupByGroupname(groupname):
    # Returns the group identified by local name 'groupname', or None if
    # there is no such group. AnonymousGroup is returned in response to
    # "anonymous".
    if groupname == "anonymous":
        return ezidapp.models.group.AnonymousGroup
    return _getGroupPrefetch(groupname=groupname)


# Datacenter


def getDatacenterBySymbol(symbol):
    # Returns the datacenter having the given symbol.
    return django.apps.apps.get_model('ezidapp', 'Datacenter').get(symbol=symbol)
