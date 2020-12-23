# =============================================================================
#
# EZID :: policy.py
#
# Authorization policy.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2010, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import ezidapp.models
from . import util2


def authorizeView(user, identifier):
    """
  Returns True if a request to view identifier metadata is authorized.
  'user' is the requestor and should be an authenticated StoreUser
  object.  'identifier' is the identifier in question; it should be a
  StoreIdentifier object.
  """
    # In EZID, essentially all identifier metadata is public.
    return not identifier.isAgentPid or user.isSuperuser


def authorizeCreate(user, prefix):
    """
  Returns True if a request to mint or create an identifier is
  authorized.  'user' is the requestor and should be an authenticated
  StoreUser object.  'prefix' may be a complete identifier or just an
  identifier prefix corresponding to a shoulder; in either case it
  must be qualified, e.g., "doi:10.5060/".
  """
    if util2.isTestIdentifier(prefix):
        return True
    if any([prefix.startswith(s.prefix) for s in user.shoulders.all()]):
        return True
    if any(authorizeCreate(u, prefix) for u in user.proxy_for.all()):
        return True
    # Note what's missing here: group and realm administrators get no
    # extra identifier creation privileges.
    if user.isSuperuser:
        return True
    return False


def authorizeUpdate(user, identifier):
    """
  Returns True if a request to update an existing identifier is
  authorized (not including ownership changes; see
  authorizeOwnershipChange below).  'user' is the requestor and should
  be an authenticated StoreUser object.  'identifier' is the
  identifier in question; it should be a StoreIdentifier object.
  """
    if identifier.owner != None:
        idOwner = identifier.owner
        idGroup = identifier.ownergroup
    else:
        idOwner = ezidapp.models.AnonymousUser
        idGroup = ezidapp.models.AnonymousGroup
    if user == idOwner:
        return True
    if user in idOwner.proxies.all():
        return True
    if user.isGroupAdministrator and user.group == idGroup:
        return True
    if user.isRealmAdministrator and user.realm == idGroup.realm:
        return True
    if user.isSuperuser:
        return True
    return False


def authorizeUpdateLegacy(user, owner, ownergroup):
    """
  Legacy version of the above function needed by the UI, which
  currently does not utilize StoreIdentifier objects.  'user' is as
  above.  'owner' and 'ownergroup' describe the ownership of the
  identifier in question; each should be a local name, e.g., "dryad".
  """
    # We create a fictitious identifier filled out just enough for the
    # above policy check to work.
    u = ezidapp.models.getUserByUsername(owner)
    g = ezidapp.models.getGroupByGroupname(ownergroup)
    i = ezidapp.models.StoreIdentifier(
        owner=(None if u is None or u.isAnonymous else u),
        ownergroup=(None if g is None or g.isAnonymous else g),
    )
    return authorizeUpdate(user, i)


# Policy-wise, deleting an identifier is the same as updating it.
# Note that we're not checking delete restrictions related to
# identifier status here; that's done in the mainline code.

authorizeDelete = authorizeUpdate


def authorizeOwnershipChange(user, currentOwner, newOwner):
    """
  Returns True if a request to change the ownership of an existing
  identifier is authorized.  'user' is the requestor and should be an
  authenticated StoreUser object.  'currentOwner' and 'newOwner'
  should also be StoreUser objects; they may be None to indicate
  anonymous ownership.
  """
    if currentOwner == None:
        currentOwner = ezidapp.models.AnonymousUser
    if newOwner == None:
        newOwner = ezidapp.models.AnonymousUser
    if newOwner == currentOwner:
        return True
    # Interesting property here: by the rule below, a common proxy can
    # act as a bridge between users in different groups.
    def userCanUpdateWhenOwnedBy(owner):
        if user == owner or user in owner.proxies.all():
            return True
        if user.isGroupAdministrator and owner.group == user.group:
            return True
        if user.isRealmAdministrator and owner.realm == user.realm:
            return True
        return False

    if userCanUpdateWhenOwnedBy(currentOwner) and userCanUpdateWhenOwnedBy(newOwner):
        return True
    if user.isSuperuser:
        return True
    return False


def authorizeDownload(user, owner=None, ownergroup=None):
    """
  Returns True if a request to download all identifiers owned by
  'owner' (given as a StoreUser object) or 'ownergroup' (given as a
  StoreGroup object) is authorized.  'user' is the requestor and
  should be an authenticated StoreUser object.  Only one of 'owner'
  and 'ownergroup' should be specified.
  """
    if owner != None:
        if user == owner:
            return True
        if user in owner.proxies.all():
            return True
        ownergroup = owner.group
    if user.isGroupAdministrator and user.group == ownergroup:
        return True
    if user.isRealmAdministrator and user.realm == ownergroup.realm:
        return True
    if user.isSuperuser:
        return True
    return False
