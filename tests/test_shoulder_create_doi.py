"""Test the shoulder-create-doi management command
"""
import django.core.management
import django.core.management.base
import freezegun
import pytest

import ezidapp.models
import tests.util.sample as sample
import tests.util.util


@freezegun.freeze_time('2010-10-11')
class TestShoulderCreateDoi:
    def test_1000(self, capsys):
        """Creating basic Crossref DOI shoulder returns expected messages"""
        assert not ezidapp.models.Shoulder.objects.filter(
            prefix='doi:10.9111/r01'
        ).exists()
        django.core.management.call_command(
            # <naan> <shoulder> <name>
            'shoulder-create-doi',
            '9111',
            'r01',
            'r01 test org',
            '--crossref',
        )
        out_str, err_str = capsys.readouterr()
        sample.assert_match(out_str, 'output')

    def test_1010(self, capsys):
        """Creating Crossref DOI shoulder creates expected database entries"""
        assert not ezidapp.models.Shoulder.objects.filter(
            prefix='doi:10.9111/r01'
        ).exists()
        django.core.management.call_command(
            # <naan> <shoulder> <name>
            'shoulder-create-doi',
            '9111',
            'r01',
            'r01 test org',
            '--crossref',
        )
        s = ezidapp.models.Shoulder.objects.filter(prefix='doi:10.9111/r01').get()
        sample.assert_match(tests.util.util.shoulder_to_dict(s), 'crossref')
        assert s.active
        assert not s.isSupershoulder
        assert not s.isTest

    def test_1020(self, capsys):
        """Creating DataCite DOI returns error if datacenter is invalid"""
        assert not ezidapp.models.Shoulder.objects.filter(
            prefix='doi:10.9111/r01'
        ).exists()
        with pytest.raises(django.core.management.base.CommandError) as e:
            django.core.management.call_command(
                # <naan> <shoulder> <name>
                'shoulder-create-doi',
                '9111',
                'r01',
                'r01 test org',
                '--datacite',
                'invalid-data-center',
            )
        out_str, err_str = capsys.readouterr()
        sample.assert_match(out_str, 'invalid_datacenter')

    def test_1030(self, capsys):
        """Creating DataCite DOI shoulder creates expected database entries"""
        assert not ezidapp.models.Shoulder.objects.filter(
            prefix='doi:10.9111/r01'
        ).exists()
        django.core.management.call_command(
            # <naan> <shoulder> <name>
            'shoulder-create-doi',
            '9111',
            'r01',
            'r01 test org',
            '--datacite',
            'CDL.UCLA',
        )
        s = ezidapp.models.Shoulder.objects.filter(prefix='doi:10.9111/r01').get()
        sample.assert_match(tests.util.util.shoulder_to_dict(s), 'datacite')
        assert s.active
        assert not s.isSupershoulder
        assert not s.prefix_shares_datacenter
        assert not s.isTest

    def test_1040(self, capsys):
        """Creating DataCite DOI shoulder creates expected database entries"""
        assert not ezidapp.models.Shoulder.objects.filter(
            prefix='doi:10.9111/r01'
        ).exists()
        django.core.management.call_command(
            # <naan> <shoulder> <name>
            'shoulder-create-doi',
            '9111',
            'r01',
            'r01 test org',
            '--datacite',
            'CDL.UCLA',
            '--super-shoulder',
            '--shares-datacenter',
            '--test',
        )
        s = ezidapp.models.Shoulder.objects.filter(prefix='doi:10.9111/r01').get()
        sample.assert_match(tests.util.util.shoulder_to_dict(s), 'datacite_flags')
        assert s.active
        assert s.isSupershoulder
        assert s.prefix_shares_datacenter
        assert s.isTest
