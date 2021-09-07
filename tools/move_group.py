#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

# Moves a group to a different realm.
#
# This script modifies the database external to the running server.
# While this script goes to some pains to ensure that the move can be
# performed safely and that there will be no conflicts with the
# server, it does not guarantee that, and hence should be run with
# caution.
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

import django.db.transaction

import ezidapp.models.group
import ezidapp.models.realm
import ezidapp.models.group
import ezidapp.models.realm

# @executable
import ezidapp.models.util

STEPS = [
    "1) Move the group (this script, step=1).",
    "2) Reload the server.",
    "3) Save the group's record in the Django admin to update its agent PID.",
    "4) Similarly save the group's user's records in the Django admin.",
]

MOVE_REQUIREMENTS = """For a group to be moved, the group must:

   - Have no users that are realm administrators"""


def error(message):
    sys.stderr.write("move-group: %s\n" % message)
    sys.exit(1)


p = argparse.ArgumentParser(
    description=(
        "Moving a group to a different realm requires 4 steps:\n\n" + "\n".join(STEPS)
    ),
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
p.add_argument("group", help="the group to move")
p.add_argument("new_realm", help="the realm to move to")
p.add_argument("step", type=int, choices=[1], nargs="?", help="processing step")

args = p.parse_args(sys.argv[1:])

group = ezidapp.models.util.getGroupByGroupname(args.group)
if group is None or args.group == "anonymous":
    error("no such group: " + args.group)

try:
    newRealm = ezidapp.models.realm.Realm.objects.get(name=args.new_realm)
except ezidapp.models.realm.Realm.DoesNotExist:
    error("no such realm: " + args.new_realm)

if any(u.isRealmAdministrator for u in group.users.all()):
    error("group can't be moved\n\n%s\n" % MOVE_REQUIREMENTS)

if args.step is None:
    p.error("run with -h for usage")

if args.step == 1:
    # noinspection PyUnboundLocalVariable,PyUnboundLocalVariable
    if newRealm == group.realm:
        error("group is already in realm, nothing to do")
    with django.db.transaction.atomic():
        group.realm = newRealm
        group.save()
        for u in group.users.all():
            u.realm = newRealm
            u.save()
    newRealm = ezidapp.models.realm.Realm.objects.get(name=newRealm.name)
    searchGroup = ezidapp.models.group.Group.objects.get(
        groupname=group.groupname
    )
    with django.db.transaction.atomic():
        searchGroup.realm = newRealm
        searchGroup.save()
        for u in searchGroup.searchuser_set.all():
            u.realm = newRealm
            u.save()
    print(
        (
            "move-group: step 1 complete\n\nRemaining steps required:\n\n{}\n".format(
                "\n".join(STEPS[1:])
            )
        )
    )
