#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Test the shoulder-list management command
"""

import pytest

import impl.nog.bdb as bdb
import impl.nog.exc
import impl.nog.id_ns
import tests.util.sample


class TestDoiUtil:
    @pytest.mark.parametrize(
        'doi,naan_or_exc',
        (
            ('0', 'b0000'),
            ('9999', 'b9999'),
            ('10000', 'c0000'),
            (0, 'b0000'),
            (1, 'b0001'),
            (9999, 'b9999'),
            (10000, 'c0000'),
            (16543, 'c6543'),
            (99999, 'n9999'),
            (199998, 'p9998'),
            (199999, 'p9999'),
            (200000, 'q0000'),
            (200001, 'q0001'),
            (200002, 'q0002'),
            (999999, 'z9999'),
            (1000000, OverflowError),
            (1000001, OverflowError),
        ),
    )
    def test_1000(self, doi, naan_or_exc, tmp_bdb_root):
        """doi_prefix_to_naan()"""
        if isinstance(naan_or_exc, str):
            assert bdb.doi_prefix_to_naan(doi, allow_lossy=True) == naan_or_exc
        else:
            with pytest.raises(naan_or_exc):
                bdb.doi_prefix_to_naan(doi, allow_lossy=True)

    @pytest.mark.parametrize(
        'ns_str,path_or_exc',
        (
            ('doi:10.1234', 'b1234/NULL'),
            ('doi:10.1234/', 'b1234/NULL'),
            ('doi:10.1234/XYZ', 'b1234/xyz'),
            ('doi:10.99999/X', 'n9999/x'),
            ('ark:/1234', '1234/NULL'),
            ('ark:/1234/', '1234/NULL'),
            ('ark:/1234/x', '1234/x'),
            ('ark:/1234/xyz', '1234/xyz'),
            ('ark:/12345', '12345/NULL'),
            ('ark:/12345/', '12345/NULL'),
            ('ark:/12345/x', '12345/x'),
            ('ark:/12345/xyz', '12345/xyz'),
            ('ark:/99999/xyz', '99999/xyz'),
        ),
    )
    def test_1030(self, ns_str, path_or_exc, tmp_bdb_root):
        """get_path(): Well formed identifiers generate the expected paths"""
        assert (
            bdb.get_path(
                ns_str,
                is_new=True,
            )
            .as_posix()
            .endswith('/{}/nog.bdb'.format(path_or_exc))
        )

    @pytest.mark.parametrize(
        'ns_str',
        (
            'doi:10.1',
            'doi:10.100000',
            'ark:/1',
            'ark:/100000/',
            'ark:/1/x',
            'ark:/100000/xyz',
        ),
    )
    def test_1031(self, ns_str, tmp_bdb_root):
        """get_path(): Invalid identifiers raise IdentifierError"""
        with pytest.raises(impl.nog.id_ns.IdentifierError):
            bdb.get_path(ns_str, 'root', is_new=True)

    @pytest.mark.parametrize(
        'ns_str',
        (
            'doi:10.100000/X',
            'doi:10.100001/X',
            'doi:10.200000',
        ),
    )
    def test_1032(self, ns_str, tmp_bdb_root):
        """get_path(): Raises IdentifierError for prefix that exceeds 5 digits"""
        with pytest.raises(impl.nog.id_ns.IdentifierError):
            bdb.get_path(ns_str, 'root', is_new=True)

    def test_1035(self, shoulder_csv, tmp_bdb_root):
        """get_path(): Yields the expected paths for shoulders that have minters"""
        result_list = []
        for ns_str, org_str, n2t_url in shoulder_csv:
            try:
                p = bdb.get_path(ns_str, is_new=True).as_posix()
            except impl.nog.exc.MinterError as e:
                p = repr(e)
            result_list.append(p.replace(tmp_bdb_root.as_posix(), ''))
        tests.util.sample.assert_match(result_list, 'get_path')

    @pytest.mark.parametrize(
        'doi_str,ark_str',
        (
            # ARKs generated from DOI by N2T doip2naan.
            ('doi:10.9999', 'ark:/b9999'),
            ('doi:10.10000', 'ark:/c0000'),
            ('doi:10.9999', 'ark:/b9999'),
            ('doi:10.10000', 'ark:/c0000'),
            ('doi:10.16543', 'ark:/c6543'),
            ('doi:10.99999', 'ark:/n9999'),
            # ('doi:10.0/', 'ark:/b0000/'),
            ('doi:10.9999/X', 'ark:/b9999/x'),
        ),
    )
    def test_1040(self, doi_str, ark_str):
        """doi_to_shadow_ark(): Matches ARKs generated from DOI by N2T doip2naan"""
        assert bdb.doi_to_shadow_ark(doi_str) == ark_str

    @pytest.mark.parametrize(
        'doi_str',
        (
            'doi:10.199998',
            'doi:10.199999',
            'doi:10.200000',
            'doi:10.200001',
            'doi:10.200002',
            'doi:10.999999',
            'doi:10.1000000',
            'doi:10.1000001',
            'doi:10.999999/XYZ',
            'doi:10.1000000/XYZ/ABC',
        ),
    )
    def test_1050(self, doi_str):
        """doi_to_shadow_ark(): Lossy conversions are rejected as by N2T doip2naan"""
        with pytest.raises(impl.nog.exc.MinterError):
            bdb.doi_to_shadow_ark(doi_str)

    def test_1060(self, shoulder_csv):
        """doi_to_shadow_ark(): Matches all imported N2T paths for non-shoulders"""
        for ns_str, org_str, n2t_url in shoulder_csv:
            # We exclude identifiers ending with "/" because most of them can only be
            # resolved via DB lookup.
            if ns_str.startswith('doi:') and not ns_str.endswith('/') and n2t_url:
                ez_str = bdb.doi_to_shadow_ark(ns_str)
                n2t_str = '{}:/{}/{}'.format(*n2t_url.split('/')[-3:])
                assert ez_str == n2t_str
