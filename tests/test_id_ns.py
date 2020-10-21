import logging

import pytest

import nog.exc
import nog.id_ns
import nog.id_ns as id_ns
import tests.util.sample as sample

log = logging.getLogger(__name__)


@pytest.mark.parametrize(
    'arg_tup, expected',
    (
        (('123',), id_ns.IdentifierError('must be "doi" or "ark"')),
        (('doi', '1234', 'XY'), id_ns.IdentifierError('it must be "/"')),
        (('ark', '1234', 'XY'), id_ns.IdentifierError('it must be "/"')),
        # These are triggered by impl.util.normalizeIdentifier(), which is currently
        # disabled because it only works on normal identifiers, not on shoulders.
        # (('doi', '1234'), id_ns.IdentifierError('Invalid identifier')),
        # (('doi', '1234', '/'), id_ns.IdentifierError('Invalid identifier')),
        # (('ark', '1234'), id_ns.IdentifierError('Invalid identifier')),
        # (('ark', '1234', '/'), id_ns.IdentifierError('Invalid identifier')),
    ),
)
def test_1000(arg_tup, expected):
    """IdNamespace(): Invalid element combinations are detected"""
    with pytest.raises(expected.__class__) as match:
        id_ns.IdNamespace(*arg_tup)
    assert str(expected) in str(match.value)


@pytest.mark.parametrize(
    'arg_tup, expected',
    (
        (('doi',), 'doi:10.'),
        (('doi',), 'doi:10.'),
        (('doi', '1234', '', 'XY'), 'doi:10.1234/XY'),
        (('ark',), 'ark:/'),
        (('ark',), 'ark:/'),
        (('ark', '12345', '', 'xy'), 'ark:/12345/xy'),
        (('ark', '12345', '/', 'xy'), 'ark:/12345/xy'),
    ),
)
def test_1010(arg_tup, expected):
    """IdNamespace(): Instantiated with separate elements, str()"""
    assert str(id_ns.IdNamespace(*arg_tup)) == expected


@pytest.mark.parametrize(
    'arg_tup, expected', ((tuple(), (None, None, None, None)),),
)
def test_1020(arg_tup, expected):
    """IdNamespace(): Instantiated with separate elements, as_tup()"""
    assert id_ns.IdNamespace(*arg_tup).as_tup() == expected


@pytest.mark.parametrize(
    'ns_str',
    (
        '',
        '123',
        'doi',
        'doi:10.',
        'ark',
        'ark:/',
    ),
)
def test_1030(ns_str):
    """IdNamespace(): Instantiated with invalid str"""
    with pytest.raises(id_ns.IdentifierError) as match:
        id_ns.IdNamespace.from_str(ns_str)


@pytest.mark.parametrize(
    'ns_str, expected_tup',
    (
        ('ark:/99999/', ('ark', '99999', '/', '')),
        ('doi:10.1234/XY', ('doi', '1234', '/', 'XY')),
    ),
)
def test_1040(ns_str, expected_tup):
    """IdNamespace(): Instantiated with invalid str"""
    assert id_ns.IdNamespace.from_str(ns_str).as_tup() == expected_tup


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
def test_1050(ns_str):
    """IdNamespace.from_str(): Attempting to split invalid namespaces raises
    MinterError """
    with pytest.raises(nog.exc.MinterError):
        nog.id_ns.IdNamespace.from_str(ns_str)


@pytest.mark.parametrize(
    'ns_str, ns_tup',
    (
        ('doi:10.1234', ('doi', '1234', None, None)),
        ('doi:10.1234/', ('doi', '1234', '/', '')),
        ('doi:10.1234/X', ('doi', '1234', '/', 'X')),
        ('doi:10.1234/XYZ', ('doi', '1234', '/', 'XYZ')),
        ('ark:/1234', ('ark', '1234', None, None)),
        ('ark:/1234/', ('ark', '1234', '/', '')),
        ('ark:/1234/x', ('ark', '1234', '/', 'x')),
        ('ark:/1234/xyz', ('ark', '1234', '/', 'xyz')),
    ),
)
def test_1060(ns_str, ns_tup):
    """IdNamespace.from_str(): Splitting valid namespaces returns expected
    components"""
    assert nog.id_ns.IdNamespace.from_str(ns_str).as_tup() == ns_tup


def test_1070(shoulder_csv):
    """IdNamespace(): Initialize from set of known good shoulders"""
    result_list = []
    for ns_str, org_str, n2t_url in shoulder_csv:
        result_list.append(
            '{:<20s} {}'.format(ns_str, id_ns.IdNamespace.from_str(ns_str).as_tup(), )
        )
    sample.assert_match(u'\n'.join(result_list), 'from_str')


def test_1080(shoulder_csv):
    """IdNamespace(): Round trip to string is lossless"""
    for ns_str, org_str, n2t_url in shoulder_csv:
        assert str(id_ns.IdNamespace.from_str(ns_str)) == ns_str
