'''
Implements test cases for the resolve functionality.


'''

import logging
import requests
import pytest

TIMEOUT_SEC = 500.0
EZID_SERVICE = "http://localhost:8000/"
_L = logging.getLogger('test_resolve')

def create_resolve_url(service, identifier):
    return f"{service}{identifier}"


def call_resolve(identifier, accept=None):
    url = create_resolve_url(EZID_SERVICE, identifier)
    headers = {
        "Accept": "*/*"
    }
    if accept is not None:
        headers['Accept'] = accept
    response = requests.get(url, headers=headers, timeout=TIMEOUT_SEC, allow_redirects=False)
    return {
        'status': response.status_code,
        'media-type': response.headers.get('content-type', None),
        'text': response.text,
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
