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
    def test_1000(self, caplog):
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

    def test_1010(self, caplog):
        """Creating Crossref DOI shoulder creates expected database entries
        for shoulder and minter."""
        prefix = 'doi:10.9111/R01'
        org_name = '91101/r01 test org'
        assert not ezidapp.models.shoulder.Shoulder.objects.filter(
            prefix=prefix
        ).exists()
        django.core.management.call_command(
            # <ns> <org-name>
            'shoulder-create-doi',
            prefix,
            org_name,
            '--crossref',
        )
        s = ezidapp.models.shoulder.Shoulder.objects.filter(
            prefix=prefix
        ).get()
        sample.assert_match(tests.util.util.shoulder_to_dict(s), 'crossref')
        assert s.active
        assert s.crossrefEnabled
        assert not s.isSupershoulder
        assert not s.isTest

        minter = ezidapp.models.minter.Minter.objects.get(prefix=prefix)
        assert minter.prefix == prefix
        assert minter.minterState['mask'] == 'eedk'

    def test_1020(self, caplog):
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

    def test_1030(self, caplog):
        """Creating DataCite DOI shoulder creates expected database entries
        for shoulder and minter."""
        prefix = 'doi:10.9111/R01'
        org_name = '91101/r01 test org'
        assert not ezidapp.models.shoulder.Shoulder.objects.filter(
            prefix='doi:10.9111/R01'
        ).exists()
        django.core.management.call_command(
            # <ns> <org-name>
            'shoulder-create-doi',
            prefix,
            org_name,
            '--datacite',
            'CDL.UCLA',
        )
        s = ezidapp.models.shoulder.Shoulder.objects.filter(
            prefix=prefix
        ).get()
        sample.assert_match(tests.util.util.shoulder_to_dict(s), 'datacite')
        assert s.active
        assert not s.crossrefEnabled
        assert not s.isSupershoulder
        assert not s.prefix_shares_datacenter
        assert not s.isTest

        minter = ezidapp.models.minter.Minter.objects.get(prefix=prefix)
        assert minter.prefix == prefix
        assert minter.minterState['mask'] == 'eedk'

    def test_1040(self, caplog):
        """Creating DataCite DOI shoulder creates expected database entries
        for shoulder and minter."""
        prefix = 'doi:10.9111/R01/'
        org_name = '91101/r01 test org'
        assert not ezidapp.models.shoulder.Shoulder.objects.filter(
            prefix='doi:10.9111/R01/'
        ).exists()
        django.core.management.call_command(
            # <ns> <org-name>
            'shoulder-create-doi',
            prefix,
            org_name,
            '--datacite',
            'CDL.UCLA',
            '--super-shoulder',
            '--shares-datacenter',
            '--test',
        )
        s = ezidapp.models.shoulder.Shoulder.objects.filter(
            prefix=prefix
        ).get()
        sample.assert_match(tests.util.util.shoulder_to_dict(s), 'datacite_flags')
        assert s.active
        assert s.isSupershoulder
        assert s.prefix_shares_datacenter
        assert s.isTest

        # no minter for a super shoulder
        assert not ezidapp.models.minter.Minter.objects.filter(prefix=prefix).exists()

