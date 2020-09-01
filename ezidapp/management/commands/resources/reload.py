import base64
import logging
import platform
import urllib
import urllib2

import django.core.management
import django.urls

import config

KNOWN_EZID_HOSTNAME_TUP = (('uc3-ezidx2-dev', 'uc3-ezidx2-stg', 'uc3-ezidx2-prd'),)


log = logging.getLogger(__name__)


def trigger_reload():
    """Refresh the in-memory caches of the running EZID process.

    If host is not one of the known EZID hostnames for dev, stage or production,
    we assume that this is running in a development environment, and we don't attempt
    to trigger a refresh.
    """
    hostname = platform.uname()[1]
    if hostname not in KNOWN_EZID_HOSTNAME_TUP:
        print(
            'Hostname "{}" not one of {}. Assuming dev env, skipping EZID reload'.format(
                hostname, ', '.join('"{}"'.format(s) for s in KNOWN_EZID_HOSTNAME_TUP)
            )
        )
        return

    ezid_base_url = config.get("DEFAULT.ezid_base_url")
    reload_path = django.urls.reverse('api.reload')
    reload_url = '{}/{}'.format(ezid_base_url.strip('/'), reload_path.strip('/'))
    admin_pw_str = config.get("auth.admin_password")

    data = urllib.urlencode({})
    request = urllib2.Request(reload_url, data=data)
    auth_b64 = base64.b64encode('%s:%s' % ('admin', admin_pw_str))
    request.add_header("Authorization", "Basic {}".format(auth_b64))

    response = urllib2.urlopen(request)
    body_str = response.read()
    if response.code != 200:
        raise Exception(
            'EZID reload trigger failed. EZID returned: status_code={} body="{}"'.format(
                response.code, body_str
            )
        )

    print('EZID reload request returned: 200 OK: {}'.format(body_str))
