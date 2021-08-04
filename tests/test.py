"""Test the test framework itself"""


def test_1000(apitest_client):
    """Test that the apitest_client fixture returns a client logged in as the apitest user
    """
    assert apitest_client is not None
    assert 'sessionid' in apitest_client.cookies
