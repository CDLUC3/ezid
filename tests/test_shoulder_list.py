"""Test the shoulder-list management command
"""

import ezidapp.management.commands.resources.shoulder as shoulder
import tests.util.sample as sample


class TestShoulderList:
    def test_1000(self, capsys):
        shoulder.dump_shoulders()
        out_str, err_str = capsys.readouterr()
        sample.assert_match(out_str, 'list')
