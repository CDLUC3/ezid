#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Authorization policy
"""

import logging

import ezidapp.models.group
import ezidapp.models.identifier
import ezidapp.models.user
import ezidapp.models.util
import impl.util2

logger = logging.getLogger(__name__)


def authorizeView(user, identifier):
    """Return True if a request to view identifier metadata is authorized

    'user' is the requestor and should be an authenticated User
    object. 'identifier' is the identifier in question; it should be a
    Identifier object.

    Basically:
      Any user can view metadata for a PID if it is not an agent PID.
      Super user can view any PID.
    """
    # In EZID, essentially all identifier metadata is public.
    logger.debug(f'Checking if user can view identifier. user="{user}" identifier="{identifier}"')
    is_authorized = not identifier.isAgentPid or user.isSuperuser
    logger.debug(f'is_authorized="{is_authorized}"')
    return is_authorized


def authorizeCreate(user, prefix):
    """Return True if a request to mint or create an identifier is authorized

    'user' is the requestor and should be an authenticated User
    object. 'prefix' may be a complete identifier or just an identifier
    prefix corresponding to a shoulder; in either case it must be
    qualified, e.g., "doi:10.5060/".
    """
    logger.debug(f'Checking if user can create identifier. user="{user}" prefix="{prefix}"')
    if impl.util2.isTestIdentifier(prefix):
        logger.debug('Authorized: Is test identifier')
        return True
    if any([prefix.startswith(s.prefix) for s in user.shoulders.all()]):
        logger.debug('Authorized: User owns shoulder starting with prefix')
        return True
    if any(authorizeCreate(u, prefix) for u in user.proxy_for.all()):
        logger.debug('Authorized: Proxy owns shoulder starting with prefix')
        return True
    # Note what's missing here: group and realm administrators get no
    # extra identifier creation privileges.
    if user.isSuperuser:
        logger.debug('Authorized: Superuser')
        return True
    logger.debug(
        'Not authorized: '
        'Not test identifier, user/proxy starting with prefix, or superuser'
    )
    return False


def authorizeUpdate(user, identifier):
    """Return True if a request to update an existing identifier is authorized
    (not including ownership changes; see authorizeOwnershipChange below).

    'user' is the requestor and should be an authenticated User
    object. 'identifier' is the identifier in question; it should be a
    Identifier object.
    """
    logger.debug(
        f'Checking if user can update identifier. user="{user}" identifier="{identifier}"'
    )
    if identifier.owner is not None:
        idOwner = identifier.owner
        idGroup = identifier.ownergroup
        logger.debug(f'Using identifier for owner and group.')
    else:
        idOwner = ezidapp.models.user.AnonymousUser
        idGroup = ezidapp.models.group.AnonymousGroup
        logger.debug(f'Using anonymous owner and group.')
    logger.debug(f'idOwner="{idOwner}" idGroup="{idGroup}"')
    if user == idOwner:
        logger.debug(f'Authorized: Owner')
        return True
    if user in idOwner.proxies.all():
        logger.debug(f'Authorized: Proxy')
        return True
    if user.isGroupAdministrator and user.group == idGroup:
        logger.debug(f'Authorized: Group admin')
        return True
    if user.isRealmAdministrator and user.realm == idGroup.realm:
        logger.debug(f'Authorized: Realm admin')
        return True
    if user.isSuperuser:
        logger.debug(f'Authorized: Superuser')
        return True
    logger.debug(f'Now authorized: Not owner, proxy, group/realm admin, or superuser')
    return False


def authorizeUpdateLegacy(user, owner, ownergroup):
    """Legacy version of the above function needed by the UI, which currently
    does not utilize Identifier objects.

    'user' is as above. 'owner' and 'ownergroup' describe the ownership
    of the identifier in question; each should be a local name, e.g.,
    "dryad".
    """
    # We create a fictitious identifier filled out just enough for the
    # above policy check to work.
    logging.debug('Checking if user can update identifier (legacy version for UI)')
    u = ezidapp.models.util.getUserByUsername(owner)
    g = ezidapp.models.util.getGroupByGroupname(ownergroup)
    i = ezidapp.models.identifier.Identifier(
        owner=(None if u is None or u.isAnonymous else u),
        ownergroup=(None if g is None or g.isAnonymous else g),
    )
    logging.debug(f'u="{u}" g="{g}" i="{i}"')
    return authorizeUpdate(user, i)


# Policy-wise, deleting an identifier is the same as updating it.
#
# We're not checking delete restrictions related to identifier status here; that's done in the
# mainline code.
authorizeDelete = authorizeUpdate


def authorizeOwnershipChange(user, currentOwner, newOwner):
    """Return True if a request to change the ownership of an existing
    identifier is authorized.

    'user' is the requestor and should be an authenticated User
    object. 'currentOwner' and 'newOwner' should also be User
    objects; they may be None to indicate anonymous ownership.
    """
    logging.debug(
        f'Checking if user can change ownership. '
        f'user="{user}" currentOwner="{currentOwner}" newOwner="{newOwner}"'
    )
    if currentOwner is None:
        currentOwner = ezidapp.models.user.AnonymousUser
    if newOwner is None:
        newOwner = ezidapp.models.user.AnonymousUser
    if newOwner == currentOwner:
        logging.debug('Authorized: New owner is same as current')
        return True

    # Interesting property here: by the rule below, a common proxy can
    # act as a bridge between users in different groups.
    def userCanUpdateWhenOwnedBy(owner):
        if user == owner or user in owner.proxies.all():
            logging.debug('Authorized: Owner or proxy')
            return True
        if user.isGroupAdministrator and owner.group == user.group:
            logging.debug('Authorized: Group admin')
            return True
        if user.isRealmAdministrator and owner.realm == user.realm:
            logging.debug('Authorized: Realm admin')
            return True
        logging.debug('Not authorized: User is not owner, proxy, group/realm admin)')
        return False

    if userCanUpdateWhenOwnedBy(currentOwner) and userCanUpdateWhenOwnedBy(newOwner):
        return True
    if user.isSuperuser:
        logging.debug('Authorized: Superuser')
        return True
    logging.debug('Not authorized')
    return False


def authorizeDownload(user, owner=None, ownergroup=None):
    """Return True if a request to download all identifiers owned by 'owner'
    (given as a User object) or 'ownergroup' (given as a Group
    object) is authorized.

    'user' is the requestor and should be an authenticated User
    object. Only one of 'owner' and 'ownergroup' should be specified.
    """
    logging.debug(
        f'Checking if user can download all identifiers owned by owner. '
        f'user="{user}" owner="{owner}" ownergroup="{ownergroup}"'
    )
    if owner is not None:
        if user == owner:
            logging.debug('Authorized: Owner')
            return True
        if user in owner.proxies.all():
            logging.debug('Authorized: Proxy')
            return True
        ownergroup = owner.group
        logging.debug(f'Changed ownergroup. ownergroup="{ownergroup}"')
    if user.isGroupAdministrator and user.group == ownergroup:
        logging.debug('Authorized: Group admin')
        return True
    if user.isRealmAdministrator and user.realm == ownergroup.realm:
        logging.debug('Authorized: Realm admin')
        return True
    if user.isSuperuser:
        logging.debug('Authorized: Superuser')
        return True
    return False
