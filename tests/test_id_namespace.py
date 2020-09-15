import pytest

import nog.exc
import nog.id_ns


class TestIdNamespace:
    @pytest.mark.parametrize(
        'ns_str',
        (
            'do:101234/xyz',
            'doi:101234/xyz',
            'doi:1.01234/xyz',
            ':1.01234/xyz',
            'ark:1234/xyz',
            'ark:101234/xyz',
            'ark:10.1234/xyz',
        ),
    )
    def test_1010(self, ns_str):
        """split_namespace(): Attempting to split invalid namespaces raises MinterError"""
        with pytest.raises(nog.exc.MinterError):
            nog.id_ns.split_namespace(ns_str)

    @pytest.mark.parametrize(
        'ns_str, ns_split',
        (
            ('doi:10.1', nog.id_ns.IdNamespace('doi:10.', '1', '')),
            ('doi:10.1234', nog.id_ns.IdNamespace('doi:10.', '1234', '')),
            ('doi:10.1234/', nog.id_ns.IdNamespace('doi:10.', '1234', '/')),
            ('doi:10.1234/X', nog.id_ns.IdNamespace('doi:10.', '1234', '/', 'X')),
            ('doi:10.1234/XYZ', nog.id_ns.IdNamespace('doi:10.', '1234', '/', 'XYZ')),
            ('ark:/1', nog.id_ns.IdNamespace('ark:/', '1', '')),
            ('ark:/1234', nog.id_ns.IdNamespace('ark:/', '1234', '')),
            ('ark:/1234/', nog.id_ns.IdNamespace('ark:/', '1234', '/')),
            ('ark:/1234/x', nog.id_ns.IdNamespace('ark:/', '1234', '/', 'x')),
            ('ark:/1234/xyz', nog.id_ns.IdNamespace('ark:/', '1234', '/', 'xyz')),
        ),
    )
    def test_1020(self, ns_str, ns_split):
        """split_namespace(): Splitting valid namespaces returns expected components"""
        assert nog.id_ns.split_namespace(ns_str) == ns_split
