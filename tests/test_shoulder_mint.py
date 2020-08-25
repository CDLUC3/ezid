"""Test the shoulder-deactivate and shoulder-activate management commands
"""
import django.conf
import django.core.management
import freezegun

import tests.util.sample as sample
import tests.util.util


@freezegun.freeze_time('2010-10-11')
class TestShoulderMint:
    def test_0100(self, capsys, tmp_bdb_root):
        namespace_str = 'ark:/33333/r3'
        tests.util.util.create_shoulder(namespace_str)
        django.core.management.call_command(
            'shoulder-mint', namespace_str, '--count', '100'
        )
        out_str, err_str = capsys.readouterr()
        sample.assert_match(out_str, 'minted')
