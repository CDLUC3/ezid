"""A class that holds the component strings of an ARK or DOI and provides
related functions."""
import collections
import logging
import re

import impl.nog.exc

log = logging.getLogger(__name__)


# noinspection PyArgumentList,PyTypeChecker,PyUnresolvedReferences
class IdNamespace(
    collections.namedtuple(
        'IdNamespace', ['scheme', 'naan_prefix', 'slash', 'shoulder']
    )
):
    """A namedtuple based class that holds the individual components of an ARK
    or DOI identifier.

    The identifier must be valid as used in EZID. It is validated and
    normalized at the time the object is created.
    """

    __slots__ = ()

    def __new__(cls, scheme=None, naan_prefix=None, slash=None, shoulder=None):
        """Create an IdNamespace from elements of an identifier.

        Args:
            With scheme=1, naan_prefix=2, slash=3 and shoulder=4, the contents
            of the elements are:

            DOI: doi:10.12345/XY
                 111----22222344

            ARK: ark:/12345/xy
                 111--22222344

            - The section marked with '---' is automatically generated as needed based
            on the scheme.
            - The slash (3) is added if shoulder is set. If shoulder is not set, the
            slash must be passed if the identifier should end with a slash.
            - None values are replaced with ''
        """
        # scheme, naan_prefix, slash, shoulder = (
        #     str(s) for s in (scheme, naan_prefix, slash, shoulder)
        # )
        if scheme and scheme not in ('doi', 'ark'):
            raise IdentifierError(
                'If scheme is set, it must be "doi" or "ark", not "{}"'.format(scheme)
            )
        if slash and slash != '/':
            raise IdentifierError(
                'If slash is set, it must be "/", not "{}"'.format(slash)
            )
        if shoulder:
            slash = '/'

        # arg_tup = tuple(str(s).strip() if s else '' for s in (scheme, naan_prefix, slash, shoulder))
        arg_tup = scheme, naan_prefix, slash, shoulder

        # TODO:
        # impl.util.normalizeIdentifier() only works on regular identifiers, not on
        # shoulders.
        # if scheme and (naan_prefix or shoulder):
        #     ns_str = IdNamespace._join(*arg_tup)
        #     normalized_ns_str = impl.util.normalizeIdentifier(ns_str)
        #     if normalized_ns_str is None:
        #         raise IdentifierError('Invalid identifier: {}'.format(ns_str))
        #     if normalized_ns_str != ns_str:
        #         return IdNamespace.from_str(normalized_ns_str)

        return super(IdNamespace, cls).__new__(cls, *arg_tup)

    @staticmethod
    def _get_sep(scheme):
        if scheme == 'doi':
            return ':10.'
        elif scheme == 'ark':
            return ':/'
        return None

    def __init__(self, *_arg_list):
        # log.debug('Created IdNamespace{}'.format(self.as_tup()))
        super(IdNamespace, self).__init__()  # scheme, sep, naan_prefix, slash, shoulder

    def __repr__(self):
        return 'IdNamespace({})'.format(str(self))

    def __str__(self):
        return IdNamespace._join(
            self.scheme, self.naan_prefix, self.slash, self.shoulder
        )

    @staticmethod
    def _join(*arg_tup):
        if len(arg_tup) >= 1:
            arg_tup = (arg_tup[0], IdNamespace._get_sep(arg_tup[0])) + arg_tup[1:]
        return ''.join([str(s).strip() if s else '' for s in arg_tup])

    def as_tup(self):
        # return self.scheme, naan_prefix, slash, shoulder
        return self.scheme, self.naan_prefix, self.slash, self.shoulder

    @staticmethod
    def from_str(ns_str):
        """Create an IdNamespace object by automatically splitting an ARK or a
        DOI. If.

        {ns_str} is already an IdNamespace, this is a no-op.
        """
        if isinstance(ns_str, IdNamespace):
            return ns_str
        if not isinstance(ns_str, str):
            raise IdentifierError('Expected a string, not {}'.format(repr(ns_str)))
        return IdNamespace.split_namespace(ns_str)

    @staticmethod
    def split_namespace(ns):
        """Split a full DOI or ARK namespace into scheme, NAAN/Prefix, slash
        and shoulder. The returned elements will always combine back to the
        full namespace.

        This also checks if the the DOI or ARK appears to be valid for
        use in EZID. If {ns} is already an IdNamespace, this is a no-op.
        """
        if isinstance(ns, IdNamespace):
            return ns
        ns_tup = IdNamespace._split_ns_to_tup(ns)
        return IdNamespace(*ns_tup)

    @staticmethod
    def split_ark_namespace(ark_ns):
        """Split a full ARK namespace into scheme, NAAN, slash and shoulder.
        The returned elements will always combine back to the full namespace.

        This also checks if the the ARK appears to be valid for use in
        EZID. If {ns} is already an IdNamespace, this is a no-op.
        """
        if isinstance(ark_ns, IdNamespace):
            return ark_ns
        doi_tup = IdNamespace._split_ark_ns_to_tup(ark_ns)
        return IdNamespace(*doi_tup)

    @staticmethod
    def split_doi_namespace(doi_ns):
        """Split a full DOI namespace into scheme, NAAN, slash and shoulder.
        The returned elements will always combine back to the full namespace.

        This also checks if the the ARK appears to be valid for use in
        EZID. If {ns} is already an IdNamespace, this is a no-op.
        """
        if isinstance(doi_ns, IdNamespace):
            return doi_ns
        doi_tup = IdNamespace._split_doi_ns_to_tup(doi_ns)
        return IdNamespace(*doi_tup)

    @staticmethod
    def _split_ns_to_tup(ns_str):
        m = re.match('(?:(ark)(?::/))|(?:(doi)(?::10\.))', str(ns_str))
        if not m:
            IdNamespace._raise_invalid_ns('DOI or ARK', ns_str)
        if m.group(1) == 'ark':
            return IdNamespace._split_ark_ns_to_tup(ns_str)
        else:
            return IdNamespace._split_doi_ns_to_tup(ns_str)

    @staticmethod
    def _split_doi_ns_to_tup(doi_ns):
        m = re.match(r'(?:(doi)(?::10.))(\d{4,5})(?:(/)([0-9A-Z./]*))?$', doi_ns)
        if not m:
            IdNamespace._raise_invalid_ns('DOI', doi_ns)
        return m.groups()

    @staticmethod
    def _split_ark_ns_to_tup(ark_ns):
        m = re.match(
            r'(?:(ark)(?::/))([0-9bcdfghjkmnpqrstvwxz]\d{3,4})(?:(/)([0-9a-z./]*))?$',
            ark_ns,
        )
        if not m:
            IdNamespace._raise_invalid_ns('ARK', ark_ns)
        return m.groups()

    @staticmethod
    def _raise_invalid_ns(type_str, ns_str):
        raise IdentifierError(
            'Invalid namespace. Expected full {}. Received: "{}"'.format(
                type_str, ns_str
            )
        )


class IdentifierError(impl.nog.exc.MinterError):
    pass
