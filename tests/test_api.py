import logging

import freezegun

import tests.util.anvl as anvl
import tests.util.sample as sample
import tests.util.util

log = logging.getLogger(__name__)


@freezegun.freeze_time('2010-10-11')
class TestAPI:
    def _mint(self, ez_admin, ns_str):
        data_bytes = anvl.format_request(
            [
                "test - who",
                "test - mint_identifier",
                "test - when",
                "2020-06-24",
                "test - what",
                "test - entry",
            ]
        ).encode('utf-8')
        response = ez_admin.post(
            "/shoulder/{}".format(tests.util.util.encode(ns_str)),
            data=data_bytes,
            content_type="text/plain; charset=UTF-8",
        )
        result_dict = anvl.response_to_dict(response.content)
        result_dict['_url'] = ns_str
        return result_dict

    def test_1000(self, ez_admin, reloaded, tmp_bdb_root, minters, log_shoulder_count):
        """Test /mint."""
        log_shoulder_count('Shoulders after test launch')
        result_list = []
        for ns, arg_tup in minters:
            result_dict = self._mint(ez_admin, str(ns))
            result_list.append(result_dict)
        # sample.assert_match(result_list, 'mint')

    def test_1010(self, ez_admin, tmp_bdb_root, minters):
        """Test /view."""
        result_list = []
        for ns, arg_tup in minters:
            result_dict = self._mint(ez_admin, str(ns))
            minted_id = result_dict['status_message']
            response = ez_admin.get(
                "/id/{}".format(tests.util.util.encode(minted_id)),
                content_type="text/plain; charset=UTF-8",
            )
            result_dict = anvl.response_to_dict(response.content)
            result_dict['_url'] = str(ns)
            if '_created' in result_dict:
                result_list.append(result_dict)
        sample.assert_match(result_list, 'view')
