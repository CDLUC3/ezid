import base64
import logging
import platform
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse

import django.core.management
import django.urls

import config

KNOWN_EZID_HOSTNAME_TUP = (
    'uc3-ezidui01x2-prd',
#    'cdl',
    'ezid-stg',
    'ezid-stg.cdlib.org',
    'uc3-ezidui01x2-stg',
    'uc3-ezidui01x2-stg.cdlib.org',
    'uc3-ezidx2-dev',
    'uc3-ezidx2-dev.cdlib.org',
    'uc3-ezidx2-prd',
    'uc3-ezidx2-prd.cdlib.org',
    'uc3-ezidx2-stg',
    'uc3-ezidx2-stg.cdlib.org',
)

log = logging.getLogger(__name__)


def trigger_reload():
    """Refresh the in-memory caches of the running EZID process.

    If host is not one of the known EZID hostnames for dev, stage or production,
    we assume that this is running in a development environment, and we don't attempt
    to trigger a refresh.
    """
    hostname = platform.uname()[1]
    if hostname not in KNOWN_EZID_HOSTNAME_TUP:
        log.info(
            'Hostname "{}" not one of {}. Assuming dev env, skipping EZID reload'.format(
                hostname, ', '.join('"{}"'.format(s) for s in KNOWN_EZID_HOSTNAME_TUP)
            )
        )
        return

    ezid_base_url = config.get("DEFAULT.ezid_base_url")
    reload_path = django.urls.reverse('api.reload')
    reload_url = '{}/{}'.format(ezid_base_url.strip('/'), reload_path.strip('/'))
    admin_pw_str = config.get("auth.admin_password")

    data = urllib.parse.urlencode({})
    request = urllib.request.Request(reload_url, data=data)
    auth_b64 = base64.b64encode('%s:%s' % ('admin', admin_pw_str))
    request.add_header("Authorization", "Basic {}".format(auth_b64))

    try:
        response = urllib.request.urlopen(request)
        body_str = response.read()
    except Exception as e:
        raise ReloadError('EZID reload trigger failed. Error: {}'.format(str(e)))

    if response.code != 200:
        raise ReloadError(
            'EZID reload trigger failed. EZID returned: status_code={} body="{}"'.format(
                response.code, body_str
            )
        )

    log.info('EZID reload request successful: {}'.format(body_str))


class ReloadError(Exception):
    pass
