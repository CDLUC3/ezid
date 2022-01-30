#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Log user out everywhere by deleting all the user's sessions
"""

import argparse
import logging

import django.core.management
import django.db.transaction

import impl.django_util
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
        parser.add_argument('user', help='The user for which to delete all sessions')
        parser.add_argument("--debug", action="store_true", help="Debug level logging")

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog.util.log_setup(__name__, opt.debug)

        n = impl.django_util.deleteSessions(opt.user)

        log.info(f'Successfully deleted {n} session(s)')
