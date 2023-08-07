#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Test the minter data modle
"""
import pytest
import logging
from django.core.exceptions import ValidationError

import ezidapp.models.minter

log = logging.getLogger(__name__)

class TestMinter:
    def test_1_invalid_values(self, caplog):
        """Validate the minter data model - invalid values"""
        caplog.set_level(logging.INFO)

        prefix='XYZark:/91101/r01/'
        minter = ezidapp.models.minter.Minter(prefix=prefix, createTime=-1, updateTime=-1, minterState='')
        with pytest.raises(ValidationError) as exc_info:
            minter.full_clean()
        
        expected_validation_errors ={
            'createTime': ["Ensure this value is greater than or equal to 0."],
            'updateTime': ["Ensure this value is greater than or equal to 0."],
            'minterState': ["This field cannot be blank."],
            'prefix': ["Invalid shoulder."],
        }
        assert exc_info.type is ValidationError
        for field_name, err_msg_list in exc_info.value.message_dict.items():
            assert expected_validation_errors.get(field_name).sort() == err_msg_list.sort()

    def test_2_field_size(self, caplog):
        """Validate the minter data model - field size"""
        caplog.set_level(logging.INFO)

        prefix='X' * 256
        minter = ezidapp.models.minter.Minter(prefix=prefix)
        with pytest.raises(ValidationError) as exc_info:
            minter.full_clean()

        expected_validation_errors = {
            'prefix': ['Invalid shoulder.', 'Ensure this value has at most 255 characters (it has 256).'],
            'minterState': ['This field cannot be blank.'],
        }
        assert exc_info.type is ValidationError
        for field_name, err_msg_list in exc_info.value.message_dict.items():
            assert expected_validation_errors.get(field_name).sort() == err_msg_list.sort()

    def test_3_default_values(self, caplog):
        """Validate default values"""
        assert not ezidapp.models.minter.Minter.objects.filter(
            prefix='ark:/91101/r01/'
        ).exists()

        prefix='ark:/91101/r01/'
        minter = ezidapp.models.minter.Minter.objects.create(prefix=prefix, minterState={})

        assert ezidapp.models.minter.Minter.objects.filter(
            prefix=prefix
        ).exists()

        minter = ezidapp.models.minter.Minter.objects.get(prefix=prefix)
        t1 = minter.createTime
        assert minter.prefix == prefix
        assert minter.createTime == minter.updateTime
        assert minter.minterState == {}

        prefix='ark:/91101/r02/'
        minter = ezidapp.models.minter.Minter.objects.create(prefix=prefix, minterState={})
        t2 = minter.createTime
        assert t2 >= t1



        

    