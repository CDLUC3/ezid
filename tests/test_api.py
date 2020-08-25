import logging

import freezegun

import impl.nog_minter
import tests.util.anvl as anvl
import tests.util.sample as sample
from tests.util.util import *

log = logging.getLogger(__name__)


@freezegun.freeze_time('2010-10-11')
class TestAPI:
    def _mint(self, ez_admin, namespace_str):
        response = ez_admin.post(
            "/shoulder/{}".format(encode(namespace_str)),
            data=anvl.format_request(
                [
                    "test - who",
                    "test - mint_identifier",
                    "test - when",
                    "2020-06-24",
                    "test - what",
                    "test - entry",
                ]
            ).encode('utf-8'),
            content_type="text/plain; charset=UTF-8",
        )
        result_dict = anvl.response_to_dict(response.content)
        return result_dict

    def test_1000(self, ez_admin, tmp_bdb_root):
        """Test /mint"""
        root_path, namespace_list = tmp_bdb_root
        namespace_str, prefix_str, shoulder_str = namespace_list[0]

        bdb_path = impl.nog_minter.get_bdb_path(prefix_str, shoulder_str)
        bdb_path = pathlib.Path(bdb_path)
        assert bdb_path.exists()

        result_dict = self._mint(ez_admin, namespace_str)
        sample.assert_match(result_dict, 'mint')

        # print('tmp_tree:\n{}'.format(dir_tree(tmp_bdb_root)))
        assert bdb_path.exists()

    def test_1010(self, ez_admin, tmp_bdb_root):
        """Test /view"""
        root_path, namespace_list = tmp_bdb_root
        namespace_str, prefix_str, shoulder_str = namespace_list[0]

        result_dict = self._mint(ez_admin, namespace_str)
        sample.assert_match(result_dict, 'mint')

        minted_id = result_dict['status_message']

        response = ez_admin.get(
            # if bang:
            #     path += "?prefix_match=yes"
            "/id/{}".format(encode(minted_id)),
            content_type="text/plain; charset=UTF-8",
        )
        result_dict = anvl.response_to_dict(response.content)
        sample.assert_match(result_dict, 'view')
