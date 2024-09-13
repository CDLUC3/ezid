#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import pytest

from django.test import RequestFactory
import impl.api as api

@pytest.fixture
def factory():
    return RequestFactory()

@pytest.mark.parametrize("val,expected",[
    ('text/plain', True),
    ('text/plain; charset=utf-8', True),
    ('text/plain; charset=US-ASCII', False),
    ('text/html', False),
    ('text/xml; charset=utf-8', False),
    ('application/json', False),
    ('application/javascript', False),
    ('application/x-www-form-urlencoded', False),
])
def test_content_type_1(factory, val, expected):
    request = factory.post('/shoulder/ark:/99999/fk4', content_type=val)
    ret = api.is_text_plain_utf8(request)
    assert ret == expected
        