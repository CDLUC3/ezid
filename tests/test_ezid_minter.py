#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import lzma
import json

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
class TestEzidMinter:
    
    def _minter_to_dict(self, file_path):
        with open(file_path) as json_file:
            return json.load(json_file)

    def test_1000(self, test_docs):
        """Minter yields identifiers matching N2T when no template extensions
        are required.

        Minter info:
            "shoulder": "77913/r7", 
            "template": "77913/r7{eedk}", 
            "total": "8410",
            "type": "rand",
            "atlast": "add3",
          
        Minter state:
            minter seq: sping (order)
            2192: 2t0f (current, 1st)
            2193: z389 (next, 2d)
            2194: t950 (3rd)
            ... ...

        This checks {MINT_COUNT} identifiers in an area where the minter
        can be stepped directly to next state.
        """
        
        # load minter to mysql
        minter_file = str(test_docs.joinpath('77913_r7.json'))
        minter_dict = self._minter_to_dict(minter_file)
        ezidapp.models.minter.Minter.objects.create(prefix=ID_STR, minterState=minter_dict)

        with lzma.open(PERL_MINTED_PATH, 'rt') as f:
            for i, python_sping in enumerate(
                impl.nog_sql.ezid_minter.mint_by_prefix(
                    ID_STR, MINT_COUNT, dry_run=True
                )
            ):
                perl_sping = f.readline().strip()
                assert (
                    perl_sping == python_sping
                ), "Mismatch after minting {} identifiers. python={} != perl={}".format(
                    i, python_sping, perl_sping
                )

    def test_1010(self, test_docs):
        """Minter yields identifiers matching N2T through a template extensions.

        Minter info:
            "shoulder": "77913/r7", 
            "template": "77913/r7{eedk}", 
            "total": "8410", 
            "type": "rand",
            "atlast": "add3"
        
        Minter state:
            minter seq: sping (order)
            8410: v582 (current, 1st)
            8411: 4x54g1d (next, 2nd)
            8412: 154dn7z (3rd)
            ... ...

        This checks identifiers in an area where the minter template must be extended
        before it can be stepped to the next state.
        """
        
        # load minter to mysql db 
        test_dataset_path = str(test_docs.joinpath('77913_r7_last_before_template_extend.json'))
        minter_dict = self._minter_to_dict(test_dataset_path)

        ezidapp.models.minter.Minter.objects.create(prefix=ID_STR, minterState=minter_dict)

        with lzma.open(PERL_MINTED_PATH, 'rt') as f:
            for i in range(6218):
                f.readline()
            for i, python_sping in enumerate(
                impl.nog_sql.ezid_minter.mint_by_prefix(
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
