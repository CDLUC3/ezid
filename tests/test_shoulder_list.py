#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Test the shoulder-list management command
"""

import logging

import impl.nog_sql.shoulder as shoulder
import tests.util.sample as sample


class TestShoulderList:
    def test_1000(self, caplog):
        caplog.set_level(logging.INFO)
        shoulder.dump_shoulders()
        sample.assert_match(caplog.text, 'list')
