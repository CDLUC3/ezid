#! /usr/bin/env python

import argparse
import sys
import time

import ezidapp.models.user
import ezidapp.models.identifier
import ezidapp.models.user

# Deletes a user, and optionally the user's identifiers as well.
#
# This script modifies the database external to the running server and
# does not, for example, participate in the server's identifier
# locking mechanism.  While this script goes to some pains to ensure
# that the deletion can be performed safely and that there will be no
# conflicts with the server, it does not guarantee that, and hence
# should be run with caution.  Note that identifier deletions are
# logged to standard error and not to the server's log.
#
# This script requires several EZID modules.  The PYTHONPATH
# environment variable must include the .../SITE_ROOT/PROJECT_ROOT
# directory; if it doesn't, we attempt to dynamically locate it and
# add it.  The DJANGO_SETTINGS_MODULE environment variable must be
# set.
#
# Greg Janee <gjanee@ucop.edu>
# June 2018
import ezidapp.models.update_queue
import ezidapp.models.util
from impl import ezid

STEPS = [
    "1) Disable the user's login and remove its shoulders.",
    "2) Delete the user (this script, step=2).",
    "3) Reload the server.",
]

DELETE_REQUIREMENTS = """For a user to be deleted, the user must:

   - Be disabled from logging in
   - Not inherit its group's shoulders
   - Have no shoulders
   - Not have any proxies or be a proxy for another user"""


def error(message):
    sys.stderr.write("delete-user: %s\n" % message)
    sys.exit(1)


p = argparse.ArgumentParser(
    description=("Deleting a user requires 3 steps:\n\n" + "\n".join(STEPS)),
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
p.add_argument("user", help="the user to delete")
p.add_argument(
    "-i",
    action="store_true",
    dest="deleteIdentifiers",
    help="also delete the user's identifiers",
)
p.add_argument(
    "-l",
    action="store_false",
    dest="updateExternalServices",
    help="disable external service updates",
)
p.add_argument("step", type=int, choices=[2], nargs="?", help="processing step")

args = p.parse_args(sys.argv[1:])

user = ezidapp.models.util.getUserByUsername(args.user)
if user is None or args.user == "anonymous":
    error("no such user: " + args.user)

if (
    user.loginEnabled
    or user.inheritGroupShoulders
    or user.shoulders.count() > 0
    or user.proxies.count() > 0
    or user.proxy_for.count() > 0
):
    error("user can't be deleted\n\n%s\n" % DELETE_REQUIREMENTS)

if args.step != 2:
    p.error("run with -h for usage")


def hasIdentifiersInUpdateQueue():
    for r in ezidapp.models.update_queue.UpdateQueue.objects.all().order_by("seq"):
        if r.actualObject.owner == user:
            return True
    return False


if args.deleteIdentifiers:
    # The loop below is designed to keep the length of the update queue
    # reasonable when deleting large numbers of identifiers.
    while True:
        ids = list(
            ezidapp.models.identifier.StoreIdentifier.objects.filter(owner=user)
            .only("identifier")
            .order_by("identifier")[:1000]
        )
        for id_str in ids:
            s = ezid.deleteIdentifier(
                id_str.identifier,
                ezidapp.models.util.getAdminUser(),
                args.updateExternalServices,
            )
            if not s.startswith("success"):
                error("identifier deletion failed: " + s)
        while hasIdentifiersInUpdateQueue():
            print("delete-user: waiting for update queue to drain...")
            sys.stdout.flush()
            time.sleep(5)
        # Placing the loop exit test here ensures the update queue is
        # drained in all cases.
        if len(ids) == 0:
            break
else:
    if ezidapp.models.identifier.StoreIdentifier.objects.filter(owner=user).count() > 0:
        error("user can't be deleted: has identifiers")
    if hasIdentifiersInUpdateQueue():
        error("user can't be deleted: has identifiers in the update queue")

searchUser = ezidapp.models.user.SearchUser.objects.get(username=user.username)
user.delete()
searchUser.delete()

s = ezid.deleteIdentifier(user.pid, ezidapp.models.util.getAdminUser())
if not s.startswith("success"):
    print("delete-user: agent PID deletion failed: " + s)

print(
    (
        "delete-user: step 2 complete\n\nRemaining steps required:\n\n%s\n"
        % "\n".join(STEPS[2:])
    )
)
