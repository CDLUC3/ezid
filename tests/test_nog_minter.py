#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import lzma

import impl.nog.bdb
import impl.nog.filesystem
import impl.nog.id_ns
import impl.nog.minter

MINT_COUNT = 1000

ID_STR = 'ark:/77913/r7'
ID_NS = impl.nog.id_ns.IdNamespace.from_str(ID_STR)
PERL_MINTED_PATH = impl.nog.filesystem.abs_path(
    "test_docs/perl_{}_{}_1000000_spings.csv.xz".format(
        ID_NS.naan_prefix, ID_NS.shoulder
    )
)


# noinspection PyClassHasNoInit,PyProtectedMember
class TestNogMinter:
    def _get_bdb_path(self, id_ns, filename_prefix_str):
        return impl.nog.filesystem.abs_path(
            "./test_docs/{}_{}{}.bdb".format(
                id_ns.naan_prefix, id_ns.shoulder, filename_prefix_str
            )
        )

    def test_1000(self, tmp_bdb_root):
        """Minter yields identifiers matching N2T when no template extensions
        are required.

        This checks {MINT_COUNT} identifiers in an area where the minter
        can be stepped directly to next state.
        """
        with lzma.open(PERL_MINTED_PATH, 'rt') as f:
            for i, python_sping in enumerate(
                impl.nog.minter.mint_by_bdb_path(
                    self._get_bdb_path(ID_NS, ''), MINT_COUNT, dry_run=True
                )
            ):
                perl_sping = f.readline().strip()
                assert (
                    perl_sping == python_sping
                ), "Mismatch after minting {} identifiers. python={} != perl={}".format(
                    i, python_sping, perl_sping
                )

    def test_1010(self, tmp_bdb_root, test_docs):
        """Minter yields identifiers matching N2T through a template
        extensions.

        This checks identifiers in an area where where the minter
        template must be extended before it can be stepped to the next
        state.
        """
        with lzma.open(PERL_MINTED_PATH, 'rt') as f:
            for i in range(6218):
                f.readline()
            for i, python_sping in enumerate(
                impl.nog.minter.mint_by_bdb_path(
                    test_docs.joinpath('77913_r7_last_before_template_extend.bdb'),
                    10,
                    dry_run=True,
                )
            ):
                perl_sping = f.readline().strip()
                assert (
                    perl_sping == python_sping
                ), "Mismatch after minting {} identifiers. python={} != perl={}".format(
                    i, python_sping, perl_sping
                )
