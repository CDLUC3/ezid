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
import datetime
import csv
from typing import List, IO, Dict, Tuple, Union

import django.apps
import django.conf
import django.core.management

import impl
import impl.nog_sql.util
import impl.util
import impl.http_client

log = logging.getLogger(__name__)

HEADER = ['Identifier',
          'URL', 
          'In SI', 
          'In LC', 
          'URL updated', 
          'SI URL', 
          'returnCode', 
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
        impl.nog_sql.util.log_setup(__name__, opt.get('debug'))

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

    def check_by_ids(self, id_list: List[str], csv_writer: IO[str]) -> None:
        """Check target urls by EZID identifiers.

        Args:
            id_list (List[str]): list of EZID identifiers
            csv_writer (IO[str]): file handler for an output file
        """
        start = datetime.datetime.now(tz=datetime.timezone.utc)
        log.info(f"begin link checker by ids: {start.strftime('%Y-%m-%d %H:%M:%S %Z')}")

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
                    ret = impl.http_client.check_url(si_url)
                    self.update_output_dict(output_dict, ret)
                
                csv_writer.writerow(output_dict)
        
        end = datetime.datetime.now(tz=datetime.timezone.utc)
        log.info(f"end link checker by ids: {end.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        log.info(f"URLs checked: {len(id_list)}, time taken: {end-start}")

    def check_by_urls(self, url_list: List[str], csv_writer: IO[str])-> None:
        """Check target urls.

        Args:
            url_list (List[str]): list of URLs
            csv_writer (IO[str]): file handler for an output file
        """
        start = datetime.datetime.now(tz=datetime.timezone.utc) 
        log.info(f"begin link checker by urls: {start.strftime('%Y-%m-%d %H:%M:%S %Z')}")

        for url in url_list:
            output_dict = {}
            output_dict['URL'] = url
            ret = impl.http_client.check_url(url)
            ret_0 = self.check_url_0(url)
            self.update_output_dict(output_dict, ret)
            self.update_output_dict_0(output_dict, ret_0)
            csv_writer.writerow(output_dict)
        
        end = datetime.datetime.now(tz=datetime.timezone.utc)
        log.info(f"end link checker by urls: {end.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        log.info(f"URLs checked: {len(url_list)}, time taken: {end-start}")
    
    def update_output_dict(self, output_dict: Dict[str, Union[str, int]], ret: Dict[str, Union[str, int]])-> None:
        """Update output dict with URL checking results.

        Args:
            output_dict (Dict[str, Union[str, int]]): original output dict
            ret (Dict[str, Union[str, int]]): dict with URL checking results

        Returns: None
        """
        ret_code = ret.get('returnCode')
        success = ret.get('success')
        log.info(f"return code: {ret_code}, success status: {success}")
        output_dict['returnCode'] = ret_code
        output_dict['mimeType'] = ret.get('mimeType')
        output_dict['size'] = ret.get('content_size')
        output_dict['error'] = ret.get('error')
    
        if not success and ret_code not in [401]:
            output_dict['Is Bad'] = "1"

    def update_output_dict_0(self, output_dict, ret):
        ret_code = ret.get('returnCode')
        success = ret.get('success')
        content = ret.get('content')
        log.info(f"return code: {ret_code}, success status: {success}")
        output_dict['returnCode_0'] = ret_code
        output_dict['mimeType_0'] = ret.get('mimeType')
        output_dict['size_0'] = len(content)
        output_dict['error_0'] = ret.get('error')
        if not success:
            output_dict['isBad_0'] = "1"

    def create_id_url_dict(self, id_list: List[str], model_name: str)-> Dict[str, str]:
        """Retrive ID and target URL from EZID database.

        Args:
            id_list (List[str]): list of EZID identifiers
            model_name (str): database model name

        Returns:
            Dict[str, str]: dict with EZID identifier as key and target url as value
        """
        model = django.apps.apps.get_model('ezidapp', model_name)
        query_set = model.objects.filter(identifier__in=id_list).order_by("identifier")
        id_url_dict = {}
        for o in query_set:
            id_url_dict[o.identifier] = o.target.strip()
        return id_url_dict

 
    def loadIdFile(self, filename: str)-> Tuple[List[str], List[str]]:
        """Read IDs and URLs from a CSV file.
            IDs are listed in the 'identifer' column;
            URLs are listed in the 'url' comumn.

        Args:
            filename (str): input filename

        Returns:
            Tuple[List[str], List[str]]: list if IDs and list of urls read from input file
        """
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
        error = ""
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
            log.error('http.client.IncompleteRead')
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
                error = "IncompleteRead: " + str(e)[:200]
        except urllib.error.HTTPError as e:
            log.error('HTTPError')
            success = False
            returnCode = e.code
            error = "HTTPError: " + str(e)[:200]
        except Exception as e:
            log.error('Exception')
            success = False
            returnCode = -1
            error = "Exception: " + str(e)[:200]
        else:
            success = True
        finally:
            if c:
                c.close()
            ret_dict = {
                'returnCode': returnCode,
                'success': success,
                'mimeType': mimeType,
                'content': content,
                'error': error,
            }
            return ret_dict


class MyHTTPErrorProcessor(urllib.request.HTTPErrorProcessor):
    def http_response(self, request, response):
        if response.status in [401, 403]:
            return response
        else:
            return urllib.request.HTTPErrorProcessor.http_response(self, request, response)

    https_response = http_response


