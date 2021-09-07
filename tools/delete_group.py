#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

# Deletes a group.
#
# This script modifies the database external to the running server and
# does not, for example, participate in the server's identifier
# locking mechanism.  While this script goes to some pains to ensure
# that the deletion can be performed safely and that there will be no
# conflicts with the server, it does not guarantee that, and hence
# should be run with caution.
#
# Identifier deletions are
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

import argparse
import sys

import ezidapp.models.group
import ezidapp.models.user
import ezidapp.models.util
from impl import ezid

STEPS = [
    "1) Delete the group's users and remove the group's shoulders.",
    "2) Delete the group (this script, step=2).",
    "3) Reload the server.",
]

DELETE_REQUIREMENTS = """For a group to be deleted, the group must:

   - Have no users
   - Have no shoulders"""


def error(message):
    sys.stderr.write("delete-group: %s\n" % message)
    sys.exit(1)


p = argparse.ArgumentParser(
    description=("Deleting a group requires 3 steps:\n\n" + "\n".join(STEPS)),
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
p.add_argument("group", help="the group to delete")
p.add_argument("step", type=int, choices=[2], nargs="?", help="processing step")

args = p.parse_args(sys.argv[1:])

group = ezidapp.models.util.getGroupByGroupname(args.group)
if group is None or args.group == "anonymous":
    error("no such group: " + args.group)

if group.users.count() > 0 or group.shoulders.count() > 0:
    error("group can't be deleted\n\n%s\n" % DELETE_REQUIREMENTS)

if args.step != 2:
    p.error("run with -h for usage")

searchGroup = ezidapp.models.group.Group.objects.get(groupname=group.groupname)
group.delete()
searchGroup.delete()

s = ezid.deleteIdentifier(group.pid, ezidapp.models.util.getAdminUser())
if not s.startswith("success"):
    print(f'delete-group: agent PID deletion failed: {s}')

print(
    (
        "delete-group: step 2 complete\n\nRemaining steps required:\n\n{}\n".format(
            "\n".join(STEPS[2:])
        )
    )
)
