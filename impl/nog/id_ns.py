"""Implement a class that holds the component strings of an ARK or DOI and provides
related functions.
"""
import collections
import re

import nog.exc


# noinspection PyArgumentList,PyTypeChecker
class IdNamespace(
    collections.namedtuple(
        'IdNamespace', ['scheme_sep', 'naan_prefix', 'slash', 'shoulder']
    )
):
    __slots__ = ()

    def __new__(cls, scheme_sep=None, naan_prefix=None, slash=None, shoulder=None):
        return super(IdNamespace, cls).__new__(
            cls, *(s or '' for s in (scheme_sep, naan_prefix, slash, shoulder))
        )

    def __repr__(self):
        return 'IdNamespace({})'.format(str(self))

    def __str__(self):
        return ''.join([self.scheme_sep, self.naan_prefix, self.slash, self.shoulder])


def split_namespace(ns):
    """Split a full DOI or ARK namespace into scheme, NAAN/Prefix, slash and shoulder.
    The returned elements will always combine back to the full namespace. If {ns} is
    already an IdNamespace, this is a no-op.
    """
    if isinstance(ns, IdNamespace):
        return ns
    m = re.match('(ark:/|doi:10\.)(.*)$', ns)
    if not m:
        _raise_invalid_ns('DOI or ARK', ns)
    if m.group(1) == 'ark:/':
        return split_ark_namespace(ns)
    else:
        return split_doi_namespace(ns)


def split_ark_namespace(ark_ns):
    """Split a full ARK namespace into scheme, NAAN, slash and shoulder. The returned
    elements will always combine back to the full namespace. If {ns} is already an
    IdNamespace, this is a no-op.
    """
    if isinstance(ark_ns, IdNamespace):
        return ark_ns
    m = re.match(r'(ark:/)(\d+)(?:(/)(.*))?', ark_ns)
    if not m:
        _raise_invalid_ns('ARK', ark_ns)
    return IdNamespace(*('' if not s else s for s in m.groups()))


def split_doi_namespace(doi_ns):
    """Split a full DOI namespace into scheme, NAAN, slash and shoulder. The returned
    elements will always combine back to the full namespace. If {ns} is already an
    IdNamespace, this is a no-op.
    """
    if isinstance(doi_ns, IdNamespace):
        return doi_ns
    m = re.match(r'(doi:10.)([\d\w]+)(?:(/)(.*))?', doi_ns)
    if not m:
        _raise_invalid_ns('DOI', doi_ns)
    return IdNamespace(*('' if not s else s for s in m.groups()))


def _raise_invalid_ns(type_str, ns_str):
    raise nog.exc.MinterError(
        'Unable to split namespace. Expected full {}. Received: "{}"'.format(
            type_str, ns_str
        )
    )
