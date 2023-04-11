#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Check target links

Link checker that tests EZID target URLs. Only non-default target URLs of public, real
identifiers are tested.

The link checker tests a target URL by performing a GET request on the URL. A timely
200 response equates to success.

"""

import http.client
import http.cookiejar
import logging
import os
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
import time

import django.apps
import django.conf
import django.core.management

import ezidapp.management.commands.proc_base
import ezidapp.models.async_queue
import ezidapp.models.identifier

# import ezidapp.models.link_checker
import ezidapp.models.user
import impl
import impl.nog.util
import impl.util

log = logging.getLogger(__name__)

class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    name = __name__
    setting = 'DAEMONS_LINKCHECKER_ENABLED'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--id_file', type=str, help='identifier file', required=True)

    def run(self):
        if self.opt.id_file:
            self.check_by_ids(self.opt.id_file)

    def now(self):
        return time.time()

    def check_by_ids(self, id_file):
        start = self.now()
        log.info(f"begin processing by ids: {start}")
        id_list = self.loadIdFile(id_file)
        if id_list and len(id_list) > 0:
            si_id_url_dict = self.create_id_url_dict(id_list, 'SearchIdentifier')
            lc_id_url_dict = self.create_id_url_dict(id_list, 'LinkChecker')

            for id in id_list:
                output_dict = {}
                output_dict["identifier"] = id
                if id not in si_id_url_dict:
                    output_dict["Not in SearchIdentifier"] = "Yes"
                if id not in lc_id_url_dict:
                    output_dict["Not in LinkChecker"] = "Yes"
                si_url = si_id_url_dict.get(id)
                lc_url = lc_id_url_dict.get(id)
                if si_url and lc_url and si_url.strip() != lc_url.strip():
                    output_dict["URL updated"] = "Yes"
                if si_url:
                    output_dict["SearchIdentifier URL"] = si_url
                    ret_code, success = self.check_url(si_url)
                    print(f"return code: {ret_code}, status: {success}")
                    if not success:
                        output_dict["URL check Failed"] = "Failed"
                
                print(output_dict)

    def create_id_url_dict(self, id_list, model_name):
        model = django.apps.apps.get_model('ezidapp', model_name)
        query_set = model.objects.filter(identifier__in=id_list).order_by("identifier")
        id_url_dict = {}
        for o in query_set:
            id_url_dict[o.identifier] = o.target.strip()
        return id_url_dict

 
    def loadIdFile(self, filename):
        if filename is None:
            return
        id_list = []
        with open(filename) as f:
            lines = f.readlines()
            for line in lines:
                if line.strip() == "" or line.startswith("#"):
                    continue
                id = line.strip()
                id_list.append(id)
  
        log.info("identifier file successfully loaded")
        return id_list


    def check_url(self, target):
        o = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
            MyHTTPErrorProcessor(),
        )
        c = None
        mimeType = "unknown"
        returnCode = 0
        success = True
        try:
            # This should probably be considered a Python bug, but urllib2
            # fails if the URL contains Unicode characters. Encoding the
            # URL as UTF-8 is sufficient.
            # Another gotcha: some websites require an Accept header.
            r = urllib.request.Request(
                target,
                headers={
                    "User-Agent": django.conf.settings.LINKCHECKER_USER_AGENT,
                    "Accept": "*/*",
                },
            )
            c = o.open(r, timeout=django.conf.settings.LINKCHECKER_CHECK_TIMEOUT)
            mimeType = c.info().get("Content-Type", "unknown")
            content = c.read(django.conf.settings.LINKCHECKER_MAX_READ)
        except http.client.IncompleteRead as e:
            log.exception('http.client.IncompleteRead')
            # Some servers deliver a complete HTML document, but,
            # apparently expecting further requests from a web browser
            # that never arrive, hold the connection open and ultimately
            # deliver a read failure. We consider these cases successes.
            # noinspection PyUnresolvedReferences
            if mimeType.startswith("text/html") and re.search(
                "</\s*html\s*>\s*$", e.partial, re.I
            ):
                success = True
                # noinspection PyUnresolvedReferences
                content = e.partial
            else:
                success = False
                returnCode = -1
        except urllib.error.HTTPError as e:
            log.exception('HTTPError')
            success = False
            returnCode = e.code
        except Exception as e:
            log.exception('Exception')
            success = False
            returnCode = -1
        else:
            success = True
        finally:
            if c:
                c.close()
            return returnCode, success


class MyHTTPErrorProcessor(urllib.request.HTTPErrorProcessor):
    def http_response(self, request, response):
        if response.status in [401, 403]:
            return response
        else:
            return urllib.request.HTTPErrorProcessor.http_response(self, request, response)

    https_response = http_response


