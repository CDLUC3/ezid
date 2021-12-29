#!/usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Test the path from an create/update/delete operation coming in from the API, through
to tasks queued for the async processes, to final push of operation to N2T, Crossref and
DataCite.
"""

import argparse
import logging

import django.core.management
import requests

import ezidapp.models.util
import impl.nog.util

log = logging.getLogger(__name__)

class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()

    def add_arguments(self, parser):
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Debug level logging',
        )

    # noinspection PyAttributeOutsideInit
    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog.util.log_setup(__name__, opt.debug)

        user = ezidapp.models.util.getUserByUsername('apitest')
        user.setPassword('apitest')

        self.call('/login')

    def call(self, path):

        assert path.startswith('/')
        host = '127.0.0.1'
        port = 8000
        # r = requests.get(f'http://{host}:{port}{path}', auth=('admin', 'admin'))
        r = requests.get(f'http://{host}:{port}{path}', auth=('apitest', 'apitest'))
        r.raise_for_status()
        print(f'Login result: {r}')

        result_list = []
        # ns, arg_tup = minters
        # result_dict = self._mint(ez_admin, ns, meta_types, test_docs)
        # minted_id = result_dict['status_message']
        # response = ez_admin.get(
        #     "/id/{}".format(tests.util.util.encode(minted_id)),
        #     content_type="text/plain; charset=utf-8",
        # )
        # result_dict = anvl.response_to_dict(response.content)
        # result_dict['_url'] = str(ns)
        # if '_created' in result_dict:
        #     result_list.append(result_dict)
        # sample.assert_match(result_list, 'view')
