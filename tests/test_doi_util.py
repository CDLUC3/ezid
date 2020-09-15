"""Test the shoulder-list management command
"""

import pytest

import impl.nog.bdb as bdb
import nog.exc
import nog.id_ns


class TestDoiUtil:
    @pytest.mark.parametrize(
        'arg_tup,repr_str',
        (
            (('a1', 'a2', 'a3', 'a4'), "IdNamespace(a1a2a3a4)"),
            (('a1', 'a2', None, None), "IdNamespace(a1a2)",),
            (('a1', '', None, ''), "IdNamespace(a1)",),
        ),
    )
    def test_0900(self, arg_tup, repr_str):
        assert repr(nog.id_ns.IdNamespace(*arg_tup)) == repr_str

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
    def test_1000(self, doi, naan_or_exc):
        """doi_prefix_to_naan()"""
        if isinstance(naan_or_exc, basestring):
            assert bdb.doi_prefix_to_naan(doi, allow_lossy=True) == naan_or_exc
        else:
            with pytest.raises(naan_or_exc):
                bdb.doi_prefix_to_naan(doi, allow_lossy=True)

    @pytest.mark.parametrize(
        'ns_str,path_or_exc',
        (
            ('doi:10.1', 'b0001/NULL'),
            ('doi:10.1234', 'b1234/NULL'),
            ('doi:10.1234/', 'b1234/NULL'),
            ('doi:10.1234/XYZ', 'b1234/xyz'),
            ('doi:10.99999/X', 'n9999/x'),

            ('doi:10.100000/X', OverflowError),
            ('doi:10.100001/X', OverflowError),
            ('doi:10.200000', OverflowError),

            ('ark:/1', '1/NULL'),
            ('ark:/1/', '1/NULL'),
            ('ark:/1/x', '1/x'),
            ('ark:/1/xyz', '1/xyz'),

            ('ark:/1234', '1234/NULL'),
            ('ark:/1234/', '1234/NULL'),
            ('ark:/1234/x', '1234/x'),
            ('ark:/1234/xyz', '1234/xyz'),

            ('ark:/12345', '12345/NULL'),
            ('ark:/12345/', '12345/NULL'),
            ('ark:/12345/x', '12345/x'),
            ('ark:/12345/xyz', '12345/xyz'),

            ('ark:/99999/xyz', '99999/xyz'),
            ('ark:/100000/xyz', '100000/xyz'),
        ),
    )
    def test_1030(self, ns_str, path_or_exc):
        """get_bdb_path_by_namespace()"""
        if isinstance(path_or_exc, basestring):
            assert bdb.get_bdb_path_by_namespace(
                ns_str, '/root'
            ).as_posix() == '/root/{}/nog.bdb'.format(path_or_exc)
        else:
            with pytest.raises(path_or_exc):
                bdb.get_bdb_path_by_namespace(ns_str, '/root')

    @pytest.mark.parametrize(
        'doi_str,ark_str',
        (
            # ARKs generated from DOI by N2T doip2naan.
            ('doi:10.0', 'ark:/b0000'),
            ('doi:10.9999', 'ark:/b9999'),
            ('doi:10.10000', 'ark:/c0000'),
            ('doi:10.0', 'ark:/b0000'),
            ('doi:10.1', 'ark:/b0001'),
            ('doi:10.9999', 'ark:/b9999'),
            ('doi:10.10000', 'ark:/c0000'),
            ('doi:10.16543', 'ark:/c6543'),
            ('doi:10.99999', 'ark:/n9999'),
            ('doi:10.0/', 'ark:/b0000/'),
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
        with pytest.raises(nog.exc.MinterError):
            bdb.doi_to_shadow_ark(doi_str)
