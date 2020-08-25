import shutil

import backports.lzma as lzma

import impl.nog_minter
import utils.filesystem

NAAN_STR = "77913"
PREFIX_STR = "r7"
NAMESPACE_STR = 'ark:/{}/{}'.format(NAAN_STR, PREFIX_STR)
MINT_COUNT = 1000


# noinspection PyClassHasNoInit,PyProtectedMember
class TestNogMinter:
    def _reset_db(self, naan_str, prefix_str):
        src_path = utils.filesystem.abs_path(
            "./test_docs/{}_{}.bdb".format(naan_str, prefix_str)
        )
        dst_path = impl.nog_minter.get_bdb_path(naan_str, prefix_str)
        utils.filesystem.create_missing_directories_for_file(dst_path)
        shutil.copy(src_path, dst_path)

    def test_1000(self, tmp_bdb_root):
        self._reset_db(NAAN_STR, PREFIX_STR)

        csv_name = "perl_{}_{}_1000000_spings.csv.xz".format(NAAN_STR, PREFIX_STR)
        csv_path = utils.filesystem.abs_path("test_docs/{}".format(csv_name))

        with lzma.open(csv_path) as f:
            for i, python_sping in enumerate(
                impl.nog_minter.mint(NAAN_STR, PREFIX_STR, MINT_COUNT, dry_run=False)
            ):
                if i == MINT_COUNT:
                    break
                perl_sping = f.readline().strip()
                assert (
                    perl_sping == python_sping
                ), "Mismatch after {} spings. python={} != perl={}".format(
                    i, python_sping, perl_sping
                )
