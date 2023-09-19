#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Test the shoulder-create-ark management command
"""

import logging

import django.core.management
import freezegun

import ezidapp.models.shoulder
import tests.util.sample as sample
import tests.util.util

log = logging.getLogger(__name__)


@freezegun.freeze_time('2010-10-11')
class TestShoulderCreateArk:
    def test_1000(self, caplog):
        """Creating basic ARK shoulder returns expected messages."""
        caplog.set_level(logging.INFO)
        assert not ezidapp.models.shoulder.Shoulder.objects.filter(
            prefix='ark:/91101/r01/'
        ).exists()
        django.core.management.call_command(
            # <ns> <org-name>
            'shoulder-create-ark',
            'ark:/91101/r01/',
            '91101/r01 test org',
        )
        sample.assert_match(caplog.text, 'output')

    def test_1010(self, caplog):
        """Creating a basic ARK shoulder creates expected database entries."""
        assert not ezidapp.models.shoulder.Shoulder.objects.filter(
            prefix='ark:/91101/r01/'
        ).exists()
        django.core.management.call_command(
            # <ns> <org-name>
            'shoulder-create-ark',
            'ark:/91101/r01/',
            '91101/r01 test org',
        )
        s = ezidapp.models.shoulder.Shoulder.objects.filter(
            prefix='ark:/91101/r01/'
        ).get()
        sample.assert_match(tests.util.util.shoulder_to_dict(s), 'basic')
        assert s.active
        assert not s.isSupershoulder
        assert not s.isTest

    def test_1020(self, caplog):
        """Creating an ARK shoulder with flags creates expected database
        entries."""
        assert not ezidapp.models.shoulder.Shoulder.objects.filter(
            prefix='ark:/91101/r01/'
        ).exists()
        django.core.management.call_command(
            # <ns> <org-name>
            'shoulder-create-ark',
            'ark:/91101/r01/',
            '91101/r01 test org',
            '--super-shoulder',
            '--test',
        )
        s = ezidapp.models.shoulder.Shoulder.objects.filter(
            prefix='ark:/91101/r01/'
        ).get()
        sample.assert_match(tests.util.util.shoulder_to_dict(s), 'flags')
        assert s.active
        assert s.isSupershoulder
        assert s.isTest

    def test_1030(self, caplog):
        """Creating a full shoulder without specifying the shoulder causes the
        minters to be stored in a separate directory named 'NULL'."""
        ns_str = 'ark:/99920/'
        org_str = '91101/r01 test org'
        assert not ezidapp.models.shoulder.Shoulder.objects.filter(
            prefix=ns_str
        ).exists()
        django.core.management.call_command(
            # <ns> <org-name>
            'shoulder-create-ark',
            ns_str,
            org_str,
            '--super-shoulder',
            '--skip-checks',
            '--test',
        )
        ezid_uri = ''
        assert ezidapp.models.shoulder.Shoulder.objects.filter(prefix=ns_str).exists()
        s = ezidapp.models.shoulder.Shoulder.objects.filter(prefix=ns_str).get()
        assert s.name == org_str
        assert s.active
        assert s.isSupershoulder
        assert s.isTest
