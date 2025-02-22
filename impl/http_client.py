import re
import requests
from typing import Dict, Union
import logging

import django.conf

log = logging.getLogger(__name__)

def check_url(url: str)->Dict[str, Union[str, int]]:
    """Tests a target URL by performing a GET request on the URL.
    
        A timely non-excptional response equates to success.
        Redirection is allowed by using the allow_redirect default setting.

    Args:
        url (str): target url to check

    Returns:
        Dict[str, Union[str, int]]: dict with folllowing keys to indicate for url checking status:
            'returnCode',
            'success',
            'mimeType',
            'content_size',
            'error',
    """
    success = False
    returnCode = -1
    mimeType = "unknown"
    content = b""
    error = ""
    content_size = 0
    chunk_size = 1024*1024  # 1MB

    try:
        response = requests.get(
            url=url,
            headers={
                "User-Agent": django.conf.settings.LINKCHECKER_USER_AGENT,
                "Accept": "*/*",
            },
            timeout=django.conf.settings.LINKCHECKER_CHECK_TIMEOUT,
            stream=True,
        )
        response.raise_for_status()
        returnCode = response.status_code
        mimeType = response.headers.get("Content-Type")
        content_size = response.headers.get("Content-Length")

        if content_size is None or content_size == 0:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    content += chunk
                if len(content) > django.conf.settings.LINKCHECKER_MAX_READ:
                    log.info("Content size exceeded LINKCHECKER_MAX_READ")
                    break
        content_size = len(content)
        success = True
    except requests.exceptions.RequestException as e:
        error = "RequestExceptio: " + str(e)[:200]
        if hasattr(e, 'response') and e.response is not None:
            returnCode = e.response.status_code
            mimeType = e.response.headers.get("Content-Type")
            content_size = e.response.headers.get("Content-Length")
            if content_size is None:
                content_size = 0

        # Note and code from ezid v.3.0
        # Some servers deliver a complete HTML document, but,
        # apparently expecting further requests from a web browser
        # that never arrive, hold the connection open and ultimately
        # deliver a read failure. We consider these cases successes.
        if mimeType.startswith("text/html") and re.search(
            "</\s*html\s*>\s*$", str(content, 'utf-8'), re.I
        ):
            success = True
            log.info("Received complete HTML page when error occurred: " + error)
        else:
            log.error(error)
    except Exception as e:
        error = "Exception: " + str(e)[:200]

    ret_dict = {
        'returnCode': returnCode,
        'success': success,
        'mimeType': mimeType,
        'content_size': content_size,
        'error': error,
    }
    return ret_dict