#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Check target links

Link checker that tests EZID target URLs provided by an input file with EZID identifiers and/or URLs.

The link checker tests a target URL by performing a GET request on the URL. A timely
200 response equates to success.

"""
import sys
import http.client
import http.cookiejar
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
import requests
import datetime
import csv

import django.apps
import django.conf
import django.core.management

import impl
import impl.nog.util
import impl.util

log = logging.getLogger(__name__)

HEADER = ['Identifier',
          'URL', 
          'In SI', 
          'In LC', 
          'URL updated', 
          'SI URL', 
          'Return Code', 
          'Is Bad',
          'mimeType',
          'size',
          'error',
          'returnCode_0', 
          'isBad_0',
          'mimeType_0',
          'size_0',
          'error_0',
          ]

class Command(django.core.management.BaseCommand):
    help = __doc__
    name = __name__

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('-i', '--id_file', type=str, help='Identifier file', required=True)
        parser.add_argument('-u', '--url', action='store_true', help='Check by target URLs')
        parser.add_argument('-o', '--output_file', type=str, help='Output file')
        parser.add_argument('--debug', action='store_true', help='Debug level logging')

    def handle(self, *args, **opt):
        impl.nog.util.log_setup(__name__, opt.get('debug'))

        if opt.get('output_file'):
            o_file = open(opt.get('output_file'), 'w')
        else:
            o_file = sys.stdout
 
        if opt.get('id_file'):
            id_list, url_list = self.loadIdFile(opt.get('id_file'))

            csv_writer = csv.DictWriter(o_file, fieldnames=HEADER)
            csv_writer.writeheader()

            if opt.get('url') and url_list:
                self.check_by_urls(url_list, csv_writer)
            else:
                self.check_by_ids(id_list, csv_writer)

    def check_by_ids(self, id_list, csv_writer):
        start = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') 
        log.info(f"begin link checker by ids: {start}")
        
        if id_list and len(id_list) > 0:
            si_id_url_dict = self.create_id_url_dict(id_list, 'SearchIdentifier')
            lc_id_url_dict = self.create_id_url_dict(id_list, 'LinkChecker')

            for id in id_list:
                output_dict = {}
                output_dict['Identifier'] = id
                if id not in si_id_url_dict:
                    output_dict['In SI'] = "No"
                if id not in lc_id_url_dict:
                    output_dict['In LC'] = "No"
                si_url = si_id_url_dict.get(id)
                lc_url = lc_id_url_dict.get(id)
                if si_url and lc_url and si_url.strip() != lc_url.strip():
                    output_dict['URL updated'] = "Yes"
                if si_url:
                    output_dict['SI URL'] = si_url
                    ret = self.check_url(si_url)
                    self.update_output_dict(output_dict, ret)
                
                csv_writer.writerow(output_dict)

    def check_by_urls(self, url_list, csv_writer):
        start = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') 
        log.info(f"begin link checker by urls: {start}")
        
        for url in url_list:
            output_dict = {}
            output_dict['URL'] = url
            ret = self.check_url(url)
            ret_0 = self.check_url_0(url)
            self.update_output_dict(output_dict, ret)
            self.update_output_dict_0(output_dict, ret_0)
            csv_writer.writerow(output_dict)

    def update_output_dict(self, output_dict, ret):
        (ret_code, success, mimeType, content_size, err_msg) = ret
        log.info(f"return code: {ret_code}, success status: {success}")
        output_dict['Return Code'] = ret_code
        output_dict['mimeType'] = mimeType
        output_dict['size'] = content_size
        output_dict['error'] = err_msg
        if not success:
            output_dict['Is Bad'] = "1"

    def update_output_dict_0(self, output_dict, ret):
        (ret_code, success, mimeType, content, err_msg) = ret
        log.info(f"return code: {ret_code}, success status: {success}")
        output_dict['returnCode_0'] = ret_code
        output_dict['mimeType_0'] = mimeType
        output_dict['size_0'] = len(content)
        output_dict['error_0'] = err_msg
        if not success:
            output_dict['isBad_0'] = "1"

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
        url_list = []
        with open(filename) as file:
            csvreader = csv.DictReader(file, delimiter='\t')
            for line in csvreader:
                identifier =  line.get('identifier')
                url = line.get('url')
                if identifier:
                    id_list.append(identifier)
                if url:
                    url_list.append(url)
  
        log.info("identifier file successfully loaded")
        return id_list, url_list


    def check_url(self, url):
        success = False
        returnCode = -1
        mimeType = "unknown"
        content = b""
        err_msg = ""
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
            err_msg = "RequestExceptio: " + str(e)[:200]
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
                log.info("Received complete HTML page when error occurred: " + err_msg)
            else:
                log.exception(err_msg)
        except Exception as e:
            err_msg = "Exception: " + str(e)[:200]

        return returnCode, success, mimeType, content_size, err_msg

    def check_url_0(self, target):
        o = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
            MyHTTPErrorProcessor(),
        )
        c = None
        mimeType = "unknown"
        returnCode = 200
        success = True
        content = ""
        err_msg = ""
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
                err_msg = "IncompleteRead: " + str(e)[:200]
        except urllib.error.HTTPError as e:
            log.exception('HTTPError')
            success = False
            returnCode = e.code
            err_msg = "HTTPError: " + str(e)[:200]
        except Exception as e:
            log.exception('Exception')
            success = False
            returnCode = -1
            err_msg = "Exception: " + str(e)[:200]
        else:
            success = True
        finally:
            if c:
                c.close()
            return returnCode, success, mimeType, content, err_msg


class MyHTTPErrorProcessor(urllib.request.HTTPErrorProcessor):
    def http_response(self, request, response):
        if response.status in [401, 403]:
            return response
        else:
            return urllib.request.HTTPErrorProcessor.http_response(self, request, response)

    https_response = http_response


