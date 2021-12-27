#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Test the shoulder-create-doi management command
"""
import logging

import django.core.management
import freezegun
import pytest

import ezidapp.models.shoulder
import tests.util.sample as sample
import tests.util.util


@freezegun.freeze_time('2010-10-11')
class TestShoulderCreateDoi:
    def test_1000(self, caplog, tmp_bdb_root):
        """Creating basic Crossref DOI shoulder returns expected messages."""
        caplog.set_level(logging.INFO)
        assert not ezidapp.models.shoulder.Shoulder.objects.filter(
            prefix='doi:10.9111/R01'
        ).exists()
        django.core.management.call_command(
            # <ns> <org-name>
            'shoulder-create-doi',
            'doi:10.9111/R01',
            '91101/r01 test org',
            '--crossref',
        )
        sample.assert_match(caplog.text, 'output')

    def test_1010(self, caplog, tmp_bdb_root):
        """Creating Crossref DOI shoulder creates expected database entries."""
        assert not ezidapp.models.shoulder.Shoulder.objects.filter(
            prefix='doi:10.9111/R01'
        ).exists()
        django.core.management.call_command(
            # <ns> <org-name>
            'shoulder-create-doi',
            'doi:10.9111/R01',
            '91101/r01 test org',
            '--crossref',
        )
        s = ezidapp.models.shoulder.Shoulder.objects.filter(
            prefix='doi:10.9111/R01'
        ).get()
        sample.assert_match(tests.util.util.shoulder_to_dict(s), 'crossref')
        assert s.active
        assert not s.isSupershoulder
        assert not s.isTest

    def test_1020(self, caplog, tmp_bdb_root):
        """Creating DataCite DOI returns error if datacenter is invalid."""
        caplog.set_level(logging.INFO)
        assert not ezidapp.models.shoulder.Shoulder.objects.filter(
            prefix='doi:10.9111/R01'
        ).exists()
        with pytest.raises(django.core.management.CommandError):
            django.core.management.call_command(
                # <ns> <org-name>
                'shoulder-create-doi',
                'doi:10.9111/R01',
                '91101/r01 test org',
                '--datacite',
                'invalid-data-center',
            )
        sample.assert_match(caplog.text, 'invalid_datacenter')

    def test_1030(self, caplog, tmp_bdb_root):
        """Creating DataCite DOI shoulder creates expected database entries."""
        assert not ezidapp.models.shoulder.Shoulder.objects.filter(
            prefix='doi:10.9111/R01'
        ).exists()
        django.core.management.call_command(
            # <ns> <org-name>
            'shoulder-create-doi',
            'doi:10.9111/R01',
            '91101/r01 test org',
            '--datacite',
            'CDL.UCLA',
        )
        s = ezidapp.models.shoulder.Shoulder.objects.filter(
            prefix='doi:10.9111/R01'
        ).get()
        sample.assert_match(tests.util.util.shoulder_to_dict(s), 'datacite')
        assert s.active
        assert not s.isSupershoulder
        assert not s.prefix_shares_datacenter
        assert not s.isTest

    def test_1040(self, caplog, tmp_bdb_root):
        """Creating DataCite DOI shoulder creates expected database entries."""
        assert not ezidapp.models.shoulder.Shoulder.objects.filter(
            prefix='doi:10.9111/R01/'
        ).exists()
        django.core.management.call_command(
            # <ns> <org-name>
            'shoulder-create-doi',
            'doi:10.9111/R01/',
            '91101/r01 test org',
            '--datacite',
            'CDL.UCLA',
            '--super-shoulder',
            '--shares-datacenter',
            '--test',
        )
        s = ezidapp.models.shoulder.Shoulder.objects.filter(
            prefix='doi:10.9111/R01/'
        ).get()
        sample.assert_match(tests.util.util.shoulder_to_dict(s), 'datacite_flags')
        assert s.active
        assert s.isSupershoulder
        assert s.prefix_shares_datacenter
        assert s.isTest
