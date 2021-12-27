#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Moves a user to a different group (and possibly realm as well)

This script modifies the database external to the running server and does not, for
example, participate in the server's identifier locking mechanism.  While this script
goes to some pains to ensure that the move can be performed safely and that there will
be no conflicts with the server, it does not guarantee that, and hence should be run
with caution.

Identifier updates are logged to standard error and not to the server's log.

This script requires several EZID modules.  The PYTHONPATH environment variable must
include the .../SITE_ROOT/PROJECT_ROOT directory; if it doesn't, we attempt to
dynamically locate it and add it.  The DJANGO_SETTINGS_MODULE environment variable must
be set.
"""

import argparse
import sys

import ezidapp.models.group
import ezidapp.models.user
import ezidapp.models.group
import ezidapp.models.identifier
import ezidapp.models.user
import ezidapp.models.async_queue
import ezidapp.models.util
from impl import ezid

STEPS = [
    "1) Disable the user's login and remove its shoulders.",
    "2) Move the user (this script, step=2).",
    "3) Reload the server.",
    "4) Move the user's identifiers (this script, step=4).",
    "5) Save the user's record in the Django admin to update its agent PID.",
    "6) Re-enable the user's login, shoulders, etc., as desired.",
]

MOVE_REQUIREMENTS = """For a user to be moved, the user must:

   - Be disabled from logging in
   - Not be privileged
   - Not inherit its current group's shoulders
   - Have no shoulders
   - Not have any proxies or be a proxy for another user"""


def error(message):
    sys.stderr.write("move-user: %s\n" % message)
    sys.exit(1)


p = argparse.ArgumentParser(
    description=(
        "Moving a user to a different group requires 6 steps:\n\n" + "\n".join(STEPS)
    ),
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
p.add_argument("user", help="the user to move")
p.add_argument("new_group", help="the group to move to")
p.add_argument("step", type=int, choices=[2, 4], nargs="?", help="processing step")

args = p.parse_args(sys.argv[1:])

user = ezidapp.models.util.getUserByUsername(args.user)
if user is None or args.user == "anonymous":
    error("no such user: " + args.user)

newGroup = ezidapp.models.util.getGroupByGroupname(args.new_group)
if newGroup is None or args.new_group == "anonymous":
    error("no such group: " + args.new_group)

if (
    user.loginEnabled
    or user.isPrivileged
    or user.inheritGroupShoulders
    or user.shoulders.count() > 0
    or user.proxies.count() > 0
    or user.proxy_for.count() > 0
):
    error("user can't be moved\n\n%s\n" % MOVE_REQUIREMENTS)

if args.step is None:
    p.error("run with -h for usage")

if args.step == 2:
    if newGroup == user.group:
        error("user is already in group, nothing to do")
    user.group = newGroup
    user.realm = newGroup.realm
    user.save()
    newGroup = ezidapp.models.group.Group.objects.get(
        groupname=newGroup.groupname
    )
    searchUser = ezidapp.models.user.User.objects.get(username=user.username)
    searchUser.group = newGroup
    searchUser.realm = newGroup.realm
    searchUser.save()
    print(
        (
            "move-user: step 2 complete\n\nRemaining steps required:\n\n{}\n".format(
                "\n".join(STEPS[2:])
            )
        )
    )

if args.step == 4:
    lastId = ""
    while True:
        ids = list(
            ezidapp.models.identifier.Identifier.objects.filter(owner=user)
            .filter(identifier__gt=lastId)
            .only("identifier")
            .order_by("identifier")[:1000]
        )
        if len(ids) == 0:
            break
        for id in ids:
            s = ezid.setMetadata(
                id.identifier,
                ezidapp.models.util.getAdminUser(),
                {"_ownergroup": newGroup.groupname},
                updateExternalServices=False,
            )
            if not s.startswith("success"):
                error("identifier move failed: " + s)
        lastId = ids[-1].identifier
    print(
        (
            "move-user: step 4 complete\n\nRemaining steps required:\n\n{}\n".format(
                "\n".join(STEPS[4:])
            )
        )
    )
