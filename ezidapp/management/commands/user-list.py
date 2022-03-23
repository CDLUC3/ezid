#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""List users
"""

import argparse
import logging

import django.core.management
import django.db.transaction

import ezidapp.models.group
import ezidapp.models.identifier
import ezidapp.models.realm
import ezidapp.models.user
import ezidapp.models.util
import impl.django_util
import impl.ezid
import impl.nog.util

log = logging.getLogger(__name__)


class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.opt = None

    def create_parser(self, *args, **kwargs):
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = argparse.RawTextHelpFormatter
        return parser

    def add_arguments(self, parser):
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Debug level logging",
        )

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog.util.log_setup(__name__, opt.debug)

        for user_model in ezidapp.models.user.User.objects.all():
            print(user_model)
