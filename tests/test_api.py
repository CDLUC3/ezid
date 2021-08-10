import datetime
import logging

import django.conf
import django.db.transaction
import freezegun

import impl.datacite
import impl.nog.util
import impl.util
import tests.util.anvl
import tests.util.metadata_generator
import tests.util.sample
import tests.util.util

log = logging.getLogger(__name__)


@freezegun.freeze_time('2010-10-11')
class TestAPI:
    def _mint(self, ez_admin, ns, meta_type=None, test_docs=None):
        meta_list = tests.util.metadata_generator._get_metadata_with_xml(ns, test_docs, meta_type)
        data_bytes = tests.util.anvl.format_request(meta_list).encode('utf-8')
        response = ez_admin.post(
            "/shoulder/{}".format(tests.util.util.encode(str(ns))),
            data=data_bytes,
            content_type="text/plain; charset=utf-8",
        )
        result_dict = tests.util.anvl.response_to_dict(response.content)
        result_dict['_url'] = ns
        return result_dict

    def _mint_by_client(self, client, ns_str):
        # meta_list = tests.util.metadata_generator._get_metadata_with_xml(ns, test_docs, meta_type)
        data_bytes = tests.util.anvl.format_request(('test_key', 'test_value')).encode('utf-8')
        response = client.post(
            "/shoulder/{}".format(tests.util.util.encode(ns_str)),
            data=data_bytes,
            content_type="text/plain; charset=utf-8",
        )
        result_dict = tests.util.anvl.response_to_dict(response.content)
        # result_dict['_url'] = ns
        return result_dict

    def test_1000(
        self,
        request,
        ez_admin,
        tmp_bdb_root,
        minters,
        log_shoulder_count,
        test_docs,
        meta_type,
    ):
        """Test /mint."""
        log_shoulder_count('Shoulders after test launch')
        result_list = []
        ns, arg_tup = minters
        result_dict = self._mint(ez_admin, ns, meta_type, test_docs)
        result_list.append(result_dict)
        tests.util.sample.assert_match(
            result_list, 'mint-{}'.format(request.node.name)
        )  # re.sub("[^\\d\\w]+", "-",request.node.name)))

    def test_1010(self, ez_admin, tmp_bdb_root, minters, test_docs, meta_type):
        """Test /view."""
        result_list = []
        ns, arg_tup = minters
        result_dict = self._mint(ez_admin, ns, meta_type, test_docs)
        minted_id = result_dict['status_message']
        response = ez_admin.get(
            "/id/{}".format(tests.util.util.encode(minted_id)),
            content_type="text/plain; charset=utf-8",
        )
        result_dict = tests.util.anvl.response_to_dict(response.content)
        result_dict['_url'] = str(ns)
        assert '_created' in result_dict
        #     result_list.append(result_dict)
        # sample.assert_match(result_list, 'view')

    # =============================================================================
    #
    # EZID :: api.py
    #
    # RESTful API to EZID services.  In the methods listed below, both
    # request bodies and response bodies have content type text/plain and
    # are formatted as ANVL.  Response character encoding is always UTF-8;
    # request character encoding must be UTF-8, and if not stated, is
    # assumed to be UTF-8.  See anvl.parse and anvl.format for additional
    # percent-encoding.  In responses, the first line is always a status
    # line.  For those methods requiring authentication, credentials may
    # be supplied using HTTP Basic authentication; thereafter, session
    # cookies may be used.  Methods provided:
    #
    # Login to obtain session cookie, nothing else:
    #   GET /login   [authentication required]
    #   response body: status line
    #
    # Logout:
    #   GET /logout
    #   response body: status line
    #
    # Get EZID's status:
    #   GET /status
    #     ?detailed={yes|no}
    #     ?subsystems={*|subsystemlist}
    #   response body: status line, optional additional status information
    #
    # Get EZID's version:
    #   GET /version
    #   response body: status line, version information
    #
    # Pause the server:
    #   GET /admin/pause?op={on|off|idlewait|monitor}   [admin auth required]
    #   request body: empty
    #   response body: status line followed by, for op=on and op=monitor,
    #     server status records streamed back indefinitely
    #
    # Reload configuration file and clear caches:
    #   POST /admin/reload   [admin authentication required]
    #   request body: empty
    #   response body: status line
    #
    # Request a batch download:
    #   POST /download_request   [authentication required]
    #   request body: application/x-www-form-urlencoded
    #   response body: status line

    def test_1020(
        self,
        apitest_client,
        minters,
        test_docs,
        meta_type,
        # tmp_bdb_root
    ):
        """
        View an identifier:
          GET /id/{identifier}   [authentication optional]
            ?prefix_match={yes|no}
          response body: status line, metadata


        Test the path from an create/update/delete operation coming in from the API, through to
        tasks queued for the async processes, to final push of operation to N2T, Crossref and
        DataCite.
        """
        # print(apitest_client)

        result_list = []
        ns, arg_tup = minters
        result_dict = self._mint(apitest_client, ns, meta_type, test_docs)
        minted_id = result_dict['status_message']

        # GET: Get

        response = apitest_client.get(
            "/id/{}".format(tests.util.util.encode(minted_id)),
            # Content-Type other than HTML is dispatched to the API
            content_type="text/plain; charset=utf-8",
        )
        result_dict = tests.util.anvl.response_to_dict(response.content)

        log.debug(f'result_dict="{result_dict}"')

        result_dict['_url'] = str(ns)

        if '_created' in result_dict:
            result_list.append(result_dict)

        impl.util.log_obj(result_list, msg='result_list')
        tests.util.sample.assert_match(result_list, 'view')

    def test_1030(
        self,
        apitest_client,
        apitest_minter,
    ):
        """
        Update an identifier:
          POST /id/{identifier}   [authentication required]
            ?update_external_services={yes|no}
          request body: optional metadata
          response body: status line

        Test the path from an update operation coming in from the API, through to tasks queued for
        the async processes, to final push of operation to N2T, Crossref and DataCite.
        """

        # We requested the apitest_client and apitest_minter fixtures, so the apitest
        # user has been successfully authenticated, and has a shoulder with minter at this point.

        # r = apitest_client.get(f'/login', auth=('apitest', 'apitest'))

        # r.raise_for_status()
        # print(f'Login result: {r}')
        # result_list = []
        # client.login(username=username, password=password)
        # r = client.get('/', auth=('apitest', 'apitest'))
        # r:HttpResponse
        # assert r.status_code == 200

        # print(apitest_minter)
        #
        # return

        # ns, arg_tup = minters

        # meta_list = tests.util.metadata_generator.get_metadata('doi:10.39999/SD2')
        meta_list = tests.util.metadata_generator.get_metadata('qwer')
        data_bytes = tests.util.anvl.format_request(meta_list).encode('utf-8')
        # metadata_anvl=anvl.format_request().response_to_dict(response.content)

        result_list = []
        result_dict = self._mint_by_client(apitest_client, apitest_minter)
        minted_id = result_dict['status_message'].decode('utf-8')

        log.debug(f'minted_id="{minted_id}"')
        log.debug('#'*100)
        r = apitest_client.post(
            "/id/{}".format(tests.util.util.encode(minted_id)),
            # Content-Type other than HTML is dispatched to the API endpoint instead of the UI.
            content_type="text/plain; charset=utf-8",
            data=data_bytes,
        )

        assert (
            r.status_code == 200
        ), f'Error. r.status_code="{r.status_code}" r.content="{r.content}"'



        # r = impl.datacite.uploadMetadata(doi[4:], {}, metadata, True, datacenter)
        # assert type(r) is not str, "unexpected return: " + r

        pass
