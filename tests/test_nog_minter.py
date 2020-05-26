import errno
import os
import shutil
import sys

import nog_minter
import backports.lzma as lzma

NAAN_STR = "77913"
PREFIX_STR = "r7"
MINT_COUNT = 1000


# noinspection PyClassHasNoInit,PyProtectedMember
class TestNogMinter:
    def _abs_path(self, rel_path):
        return os.path.abspath(
            # This returns the path of the pytest assertion, not this file
            #os.path.join(os.path.dirname(sys._getframe(1).f_code.co_filename), rel_path)
            os.path.join(os.path.dirname(__file__), rel_path)
        )

    def _reset_db(self, naan_str, prefix_str):
        src_path = self._abs_path("./test_docs/{}_{}.bdb".format(naan_str, prefix_str))
        dst_path = self._abs_path(
            "../db/minters/{}/{}/nog.bdb".format(naan_str, prefix_str)
        )
        self.mkdir_p(dst_path)
        shutil.copy(src_path, dst_path)

    def mkdir_p(self, file_path):
        dir_path = os.path.dirname(file_path)
        try:
            os.makedirs(dir_path)
        except OSError as e:
            if not (e.errno == errno.EEXIST and os.path.isdir(dir_path)):
                raise

    def test_1000(self):
        self._reset_db(NAAN_STR, PREFIX_STR)

        csv_name = "perl_{}_{}_1000000_spings.csv.xz".format(
            NAAN_STR, PREFIX_STR
        )
        csv_path = self._abs_path("test_docs/{}".format(csv_name))

        with lzma.open(csv_path) as f:

            for i, python_sping in enumerate(
                nog_minter.mint(NAAN_STR, PREFIX_STR, MINT_COUNT, dry_run=True)
            ):
                if i == MINT_COUNT:
                    break
                perl_sping = "{}/{}{}".format(
                    NAAN_STR, PREFIX_STR, f.readline().strip()
                )
                assert (
                    perl_sping == python_sping
                ), "Mismatch after {} spings. {} != {}".format(
                    i, perl_sping, python_sping
                )
