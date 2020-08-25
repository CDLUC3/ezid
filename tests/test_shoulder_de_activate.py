"""Test the shoulder-deactivate and shoulder-activate management commands
"""
import django.conf
import django.core.management
import freezegun
import pytest

import ezidapp.models
import tests.util.sample as sample
import tests.util.util


@freezegun.freeze_time('2010-10-11')
class TestShoulderDeactivateActivate:
    def test_0100(self, capsys):
        """Deactivating a shoulder that is already deactivated returns error"""
        s = ezidapp.models.Shoulder.objects.filter(prefix='ark:/87610/t6').get()
        assert not s.active
        with pytest.raises(
            django.core.management.base.CommandError, match='already deactivated'
        ):
            django.core.management.call_command(
                # <naan> <shoulder> <name>
                'shoulder-deactivate',
                'ark:/87610/t6',
            )

    def test_0110(self, capsys):
        """Activating a shoulder that is already activated returns error"""
        s = ezidapp.models.Shoulder.objects.filter(prefix='doi:10.18739/A2').get()
        assert s.active
        with pytest.raises(
            django.core.management.base.CommandError, match='already activated'
        ):
            django.core.management.call_command(
                # <naan> <shoulder> <name>
                'shoulder-activate',
                'doi:10.18739/A2',
            )

    def test_1000(self, capsys):
        """Deactivating a shoulder causes expected change in database"""
        s = ezidapp.models.Shoulder.objects.filter(prefix='doi:10.18739/A2').get()
        assert s.active
        django.core.management.call_command(
            # <naan> <shoulder> <name>
            'shoulder-deactivate',
            'doi:10.18739/A2',
        )
        s = ezidapp.models.Shoulder.objects.filter(prefix='doi:10.18739/A2').get()
        assert not s.active
        sample.assert_match(tests.util.util.shoulder_to_dict(s), 'deactivated')

    def test_1010(self, capsys):
        """Activating a shoulder causes expected change in database"""
        s = ezidapp.models.Shoulder.objects.filter(prefix='ark:/87610/t6').get()
        assert not s.active
        django.core.management.call_command(
            # <naan> <shoulder> <name>
            'shoulder-activate',
            'ark:/87610/t6',
        )
        s = ezidapp.models.Shoulder.objects.filter(prefix='ark:/87610/t6').get()
        assert s.active
        sample.assert_match(tests.util.util.shoulder_to_dict(s), 'activated')
