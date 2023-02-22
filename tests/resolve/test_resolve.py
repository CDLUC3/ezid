'''
Implements test cases for the resolve functionality.


'''

import logging
import django.test.client
import pytest

_L = logging.getLogger('test_resolve')


def call_resolve(identifier, accept=None):
    url = f"/{identifier}"
    headers = {
        "Accept": "*/*"
    }
    if accept is not None:
        headers['Accept'] = accept
    response = django.test.client.Client().get(url, headers=headers, allow_redirects=False)
    return {
        'status': response.status_code,
        'media-type': response.headers.get('content-type', None),
        'text': response.content,
        'location': response.headers.get("Location"),
    }


@pytest.mark.parametrize("val,expected",[
    ('ark:/99166/',(404,"","")),
    ('ark:/99166/p3wp9v20',(404,"","")),
    ('ark:/99166/p3wp9v205',(302,"https://ezid.cdlib.org/id/ark:/99166/p3wp9v205","")),
    ('ark:/99166/p3wp9v205?', (302, "", "")),
    ('ark:/99166/p3wp9v205??', (200, "", "")),
    ('ark:/99166/p3wp9v205?info', (200, "", "")),
    ('ark:/99166/p3wp9v205_extra', (302, "", "")),
    ('ark:/99166/p3wp9v205%20extra', (302, "", "")),
    ('ark:/99166/p3wp9v20??', (200, "", "")),
])
def test_existing(val,expected):
    res = call_resolve(val)
    assert res['status'] == expected[0]
    _L.debug(res['location'])
