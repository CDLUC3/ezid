#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Test the minter data modle
"""
import pytest
import logging
from django.core.exceptions import ValidationError

import django.conf
import ezidapp.models.group

log = logging.getLogger(__name__)

class TestGroup:
    def test_1_create_group(self, caplog, agent_minter):
        """test - Create group with group ID minted on Agent shoulder"""
        caplog.set_level(logging.INFO)

        next_spin = '4w25'
        expected_pid = f'{django.conf.settings.SHOULDERS_AGENT}{next_spin}'

        assert not ezidapp.models.group.Group.objects.filter(
            pid=expected_pid
        ).exists()

        group = ezidapp.models.group.Group(
            groupname='testgroup',
            organizationName = "Test Group",
            realm_id = 1,
            )
        with pytest.raises(ValidationError) as exc_info:
             group.full_clean()

        group.save()

        assert ezidapp.models.group.Group.objects.filter(
            pid=expected_pid
        ).exists()

        group = ezidapp.models.group.Group.objects.get(pid=expected_pid)

        assert group.pid == expected_pid
        assert group.groupname == 'testgroup'
        assert group.organizationName == 'Test Group'
        assert group.realm_id == 1


        
       

    