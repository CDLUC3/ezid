'''
Implements test cases for the resolve functionality.


'''

import logging
import requests
import pytest

TIMEOUT_SEC = 5.0
EZID_SERVICE = "http://localhost:8000/"
_L = logging.getLogger('test_resolve')

def create_resolve_url(service, identifier):
    return f"{service}{identifier}"


def call_resolve(identifier, accept=None):
    url = create_resolve_url(EZID_SERVICE, identifier)
    headers = {
        "Accept": "*"
    }
    if accept is not None:
        headers['Accept'] = accept
    response = requests.get(url, headers=headers, timeout=TIMEOUT_SEC)
    return {
        'status': response.status_code,
        'media-type': response.headers.get('content-type', None),
        'text': response.text,
    }


@pytest.mark.parametrize("val,expected",[
    ('ark:/87607/c7gf0pc7k',(200,"","")),
    ('ark:/87607/c7gf0pc7k?', (200, "", "")),
    ('ark:/87607/c7gf0pc7k??', (200, "", "")),
    ('ark:/87607/c7gf0pc7k?info', (200, "", ""))
])
def test_existing(val,expected):
    res = call_resolve(val)
    assert res['status'] == expected[0]
    _L.debug(res['text'])
