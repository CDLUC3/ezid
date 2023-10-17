#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Test the minter data modle
"""
import pytest
import logging
from django.core.exceptions import ValidationError

import django.conf
import ezidapp.models.user

log = logging.getLogger(__name__)

class TestUser:
    def test_1_create_group_and_user(self, caplog, agent_minter):
        """test - Create group and user with IDs minted on the Agent shoulder"""

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

        next_spin = '159n'
        expected_pid = f'{django.conf.settings.SHOULDERS_AGENT}{next_spin}'

        assert not ezidapp.models.user.User.objects.filter(
            pid=expected_pid
        ).exists()

        user = ezidapp.models.user.User(
            username='testuser',
            displayName = "Test User",
            group_id = group.id,
            realm_id = 1,
            )
        with pytest.raises(ValidationError) as exc_info:
             user.full_clean()

        user.save()

        assert ezidapp.models.user.User.objects.filter(
            pid=expected_pid
        ).exists()

        user = ezidapp.models.user.User.objects.get(pid=expected_pid)

        assert user.pid == expected_pid
        assert user.username == 'testuser'
        assert user.displayName == 'Test User'
        assert user.group_id == group.id
        assert user.realm_id == 1
        assert user.accountEmail == ''
        assert user.password != ''


        
       

    