import logging

import freezegun

import tests.util.anvl as anvl
import tests.util.metadata_generator
import tests.util.sample as sample
import tests.util.util

log = logging.getLogger(__name__)


@freezegun.freeze_time('2010-10-11')
class TestAPI:
    def _mint(self, ez_admin, ns, meta_type=None, test_docs=None):
        meta_list = tests.util.metadata_generator.get_metadata(ns, test_docs, meta_type)
        data_bytes = anvl.format_request(meta_list).encode('utf-8')
        response = ez_admin.post(
            "/shoulder/{}".format(tests.util.util.encode(str(ns))),
            data=data_bytes,
            content_type="text/plain; charset=utf-8",
        )
        result_dict = anvl.response_to_dict(response.content)
        result_dict['_url'] = ns
        return result_dict

    def test_1000(self, request, ez_admin, reloaded, tmp_bdb_root, minters, log_shoulder_count, test_docs, meta_types):
        """Test /mint."""
        log_shoulder_count('Shoulders after test launch')
        result_list = []
        ns, arg_tup = minters
        result_dict = self._mint(ez_admin, ns, meta_types, test_docs)
        result_list.append(result_dict)
        sample.assert_match(result_list, 'mint-{}'.format(request.node.name))#re.sub("[^\d\w]+", "-",request.node.name)))

    def test_1010(self, ez_admin, tmp_bdb_root, minters, test_docs, meta_types):
        """Test /view."""
        result_list = []
        ns, arg_tup = minters
        result_dict = self._mint(ez_admin, ns, meta_types, test_docs)
        minted_id = result_dict['status_message']
        response = ez_admin.get(
            "/id/{}".format(tests.util.util.encode(minted_id)),
            content_type="text/plain; charset=utf-8",
        )
        result_dict = anvl.response_to_dict(response.content)
        result_dict['_url'] = str(ns)
        if '_created' in result_dict:
            result_list.append(result_dict)
        sample.assert_match(result_list, 'view')
