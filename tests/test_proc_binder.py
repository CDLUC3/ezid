#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Test the shoulder-create-ark management command.
"""

import logging

import django.core.management
import freezegun

import ezidapp.models.shoulder
import tests.util.sample as sample
import tests.util.util

log = logging.getLogger(__name__)


def test_create_fixtures():
    import tests.conftest
    tests.conftest.create_fixtures()


# @freezegun.freeze_time('2010-10-11')
# class TestProcBinder:
#     def test_1000(self, registration_queue, block_outgoing):
#         django.core.management.call_command(
#             "proc-binder",
#             # exclude=["auth.permission", "contenttypes"],
#             # database=db_key,
#             # stdout=buf,
#         )
