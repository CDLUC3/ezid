#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Test the shoulder-deactivate and shoulder-activate management commands
"""

import logging

import django.conf
import django.core.management
import freezegun

import tests.util.sample as sample
import tests.util.util


@freezegun.freeze_time('2010-10-11')
class TestShoulderMint:
    def test_0100(self, caplog):
        caplog.set_level(logging.INFO)
        namespace_str = 'ark:/33333/r3'
        tests.util.util.create_shoulder(namespace_str)
        django.core.management.call_command('shoulder-mint', namespace_str, '--count', '2')
        sample.assert_match(caplog.text, 'minted')
