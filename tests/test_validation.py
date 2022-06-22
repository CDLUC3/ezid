#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Test ezidapp.models.validation
"""

import pytest

import ezidapp.models.validation

#TODO: Flesh out the test cases to match all the possibilities in the tested method
@pytest.mark.parametrize("test,expected",[
    ('1961', '1961'),
    ('196104','1961-04'),
    ('20201201', '2020-12-01'),
])
def test_publicationDate(test, expected):
    res = ezidapp.models.validation.publicationDate(test)
    assert res == expected

