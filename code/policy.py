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
import util2

def authorizeView (user, identifier, metadata):
  """
  Returns True if a request to view identifier metadata is authorized.
  'user' is the requestor and should be an authenticated StoreUser
  object.  'identifier' is the identifier in question; it must be
  qualified, as in "doi:10.5060/FOO".  'metadata' is the identifier's
  metadata as a dictionary of (name, value) pairs.
  """
  # In EZID, essentially all identifier metadata is public.  N.B.: The
  # need for the 'metadata' argument will go away when EZID uses a
  # Django model for identifiers, for then the identifier can be
  # directly queried as to whether it is an agent identifier or not.
  if "_ezid_role" not in metadata: return True
  if user.isSuperuser: return True
  return False

def authorizeCreate (user, identifier):
  """
  Returns True if a request to mint or create an identifier is
  authorized.  'user' is the requestor and should be an authenticated
  StoreUser object.  'identifier' may be a complete identifier or just
  an identifier prefix corresponding to a shoulder; in either case it
  must be qualified, e.g., "doi:10.5060/".
  """
  if util2.isTestIdentifier(identifier): return True
  if any(map(lambda s: identifier.startswith(s.prefix), user.shoulders.all())):
    return True
  # Note what's missing here: group and realm administrators get no
  # extra identifier creation privileges.
  if user.isSuperuser: return True
  return False

def authorizeUpdate (user, identifier, owner, ownergroup, localNames=False):
  """
  Returns True if a request to update an existing identifier is
  authorized (not including ownership changes; see
  authorizeOwnershipChange below).  'user' is the requestor and should
  be an authenticated StoreUser object.  'identifier' is the
  identifier in question; it must be qualified, as in
  "doi:10.5060/FOO".  'owner' and 'ownergroup' are the identifier's
  ownership attributes; if localNames is True, they should each be
  local names, e.g., "smith", otherwise they should each be qualified
  ARK identifiers, e.g., "ark:/99166/bar".
  """
  # N.B.: The need for the last three arguments will go away when EZID
  # uses a Django model for identifiers, for then the identifier's
  # ownership can be directly queried.
  if localNames:
    owner = ezidapp.models.getUserByUsername(owner)
  else:
    owner = ezidapp.models.getUserByPid(owner)
  if user == owner: return True
  if user in owner.proxies.all(): return True
  if localNames:
    ownergroup = ezidapp.models.getGroupByGroupname(ownergroup)
  else:
    ownergroup = ezidapp.models.getGroupByPid(ownergroup)
  if user.isGroupAdministrator and user.group == ownergroup: return True
  if user.isRealmAdministrator and user.realm == ownergroup.realm: return True
  if user.isSuperuser: return True
  return False

# Policy-wise, deleting an identifier is the same as updating it.
# Note that we're not checking delete restrictions related to
# identifier status here; that's done in the mainline code.

authorizeDelete = authorizeUpdate

def authorizeOwnershipChange (user, identifier, currentOwner, newOwner,
  localNames=False):
  """
  Returns True if a request to change the ownership of an existing
  identifier is authorized.  'user' is the requestor and should be an
  authenticated StoreUser object.  'identifier' is the identifier in
  question; it must be qualified, as in "doi:10.5060/FOO".  If
  localNames is True, currentOwner and newOwner should each be local
  names, e.g., "smith", otherwise they should each be qualified ARK
  identifiers, e.g., "ark:/99166/bar".
  """
  # N.B.: The need for the currentOwner and localNames arguments will
  # go away when EZID uses a Django model for identifiers, for then
  # the identifier's ownership can be directly queried.
  if newOwner == currentOwner: return True
  if localNames:
    currentOwner = ezidapp.models.getUserByUsername(currentOwner)
    newOwner = ezidapp.models.getUserByUsername(newOwner)
  else:
    currentOwner = ezidapp.models.getUserByPid(currentOwner)
    newOwner = ezidapp.models.getUserByPid(newOwner)
  # Interesting property here: by the rule below, a common proxy can
  # act as a bridge between users in different groups.
  def canUpdateWhenOwnedBy (owner):
    if user == owner or user in owner.proxies.all(): return True
    if user.isGroupAdministrator and owner.group == user.group: return True
    if user.isRealmAdministrator and owner.realm == user.realm: return True
    return False
  if canUpdateWhenOwnedBy(currentOwner) and canUpdateWhenOwnedBy(newOwner):
    return True
  if user.isSuperuser: return True
  return False

def authorizeDownload (user, owner=None, ownergroup=None):
  """
  Returns True if a request to download all identifiers owned by
  'owner' (given as a StoreUser object) or 'ownergroup' (given as a
  StoreGroup object) is authorized.  'user' is the requestor and
  should be an authenticated StoreUser object.  Only one of 'owner'
  and 'ownergroup' should be specified.
  """
  if owner != None:
    if user == owner: return True
    if user in owner.proxies.all(): return True
    ownergroup = owner.group
  if user.isGroupAdministrator and user.group == ownergroup: return True
  if user.isRealmAdministrator and user.realm == ownergroup.realm: return True
  if user.isSuperuser: return True
  return False

def authorizeCrossref (user, identifier):
  """
  Returns True if a request to register an identifier with CrossRef is
  authorized.  'user' is the requestor and should be an authenticated
  StoreUser object.  'identifier' is the identifier in question; it
  must be qualified, as in "doi:10.5060/FOO".
  """
  s = ezidapp.models.getLongestShoulderMatch(identifier)
  if s == None:
    # It's unlikely that the shoulder will have disappeared.  But if
    # it has, we take it as a sign that CrossRef is no longer
    # supported.
    return False
  return (user.crossrefEnabled or user.isSuperuser) and s.crossrefEnabled
