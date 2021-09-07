"""Test the test framework itself"""


#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

def test_1000(apitest_client):
    """Test that the apitest_client fixture returns a client logged in as the apitest user
    """
    assert apitest_client is not None
    assert 'sessionid' in apitest_client.cookies
