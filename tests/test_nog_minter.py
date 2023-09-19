#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import re
import lzma
import pathlib

import impl.nog_bdb.bdb
import impl.nog_sql.filesystem
import impl.nog_sql.id_ns
import impl.nog_sql.ezid_minter
import ezidapp.models.minter

MINT_COUNT = 1000

ID_STR = 'ark:/77913/r7'
ID_NS = impl.nog_sql.id_ns.IdNamespace.from_str(ID_STR)
PERL_MINTED_PATH = impl.nog_sql.filesystem.abs_path(
    "test_docs/perl_{}_{}_1000000_spings.csv.xz".format(
        ID_NS.naan_prefix, ID_NS.shoulder
    )
)


# noinspection PyClassHasNoInit,PyProtectedMember
class TestNogMinter:
    def _get_bdb_path(self, id_ns, filename_prefix_str):
        return impl.nog_sql.filesystem.abs_path(
            "./test_docs/{}_{}{}.bdb".format(
                id_ns.naan_prefix, id_ns.shoulder, filename_prefix_str
            )
        )
    
    def _minter_to_dict(self, bdb_path):
        bdb_obj = impl.nog_bdb.bdb.open_bdb(bdb_path)
        
        def b2s(b):
            if isinstance(b, bytes):
                return b.decode('utf-8')
            return b
        
        # remove prefix ":/" from the keys
        # for example: 
        #   ":/c0/top" -> "c0/top", 
        #   ":/saclist" -> "saclist"
        def remove_prefix(s):
            return re.sub('^(:/)', '', s)
 
        bdb_dict = {remove_prefix(b2s(k)): b2s(v) for (k, v) in bdb_obj.items()}
        return bdb_dict

    def test_1000(self, tmp_bdb_root):
        """Minter yields identifiers matching N2T when no template extensions
        are required.

        This checks {MINT_COUNT} identifiers in an area where the minter
        can be stepped directly to next state.
        """
        # load bdb file to mysql db 
        bdb_path = pathlib.Path(self._get_bdb_path(ID_NS, ''))
        bdb_dict = self._minter_to_dict(bdb_path)

        ezidapp.models.minter.Minter(prefix=ID_STR, minterState=bdb_dict)
        ezidapp.models.minter.Minter.objects.create(prefix=ID_STR, minterState=bdb_dict)

        with lzma.open(PERL_MINTED_PATH, 'rt') as f:
            for i, python_sping in enumerate(
                impl.nog_sql.ezid_minter.mint_by_bdb_path(
                    ID_STR, MINT_COUNT, dry_run=True
                )
            ):
                perl_sping = f.readline().strip()
                assert (
                    perl_sping == python_sping
                ), "Mismatch after minting {} identifiers. python={} != perl={}".format(
                    i, python_sping, perl_sping
                )

    def test_1010(self, tmp_bdb_root, test_docs):
        """Minter yields identifiers matching N2T through a template extensions.

        This checks identifiers in an area where the minter template must be extended
        before it can be stepped to the next state.
        """
        # load bdb file to mysql db 

        bdb_path = pathlib.Path(test_docs.joinpath('77913_r7_last_before_template_extend.bdb'))
        bdb_dict = self._minter_to_dict(bdb_path)

        ezidapp.models.minter.Minter(prefix=ID_STR, minterState=bdb_dict)
        ezidapp.models.minter.Minter.objects.create(prefix=ID_STR, minterState=bdb_dict)

        with lzma.open(PERL_MINTED_PATH, 'rt') as f:
            for i in range(6218):
                f.readline()
            for i, python_sping in enumerate(
                impl.nog_sql.ezid_minter.mint_by_bdb_path(
                    ID_STR,
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
