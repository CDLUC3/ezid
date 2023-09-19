#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Minter BerkeleyDB related utilities
"""

import logging
import pathlib
import re

import bsddb3
import django.conf
import django.core
import django.db
import hjson

import ezidapp.models.shoulder
import impl.nog_bdb.bdb_wrapper
import impl.nog_sql.exc
import impl.nog_sql.filesystem
import impl.nog_sql.id_ns

log = logging.getLogger(__name__)

MINTER_TEMPLATE_PATH = impl.nog_sql.filesystem.abs_path("../../etc/minter_template.hjson")


def dump_by_ns(ns, root_path=None, compact=True):
    bdb_path = get_path(ns, root_path)
    return dump(bdb_path, compact)


def as_hjson_by_shoulder(ns, root_path=None, compact=True):
    bdb_path = get_path(ns, root_path)
    return as_hjson(bdb_path, compact)


def as_dict_by_shoulder(ns, root_path=None, compact=True):
    bdb_path = get_path(ns, root_path)
    return as_dict(bdb_path, compact)


def dump(bdb_path, compact=True):
    """Dump the state of a minter BerkeleyDB to stdout as HJSON.

    Only the fields used by EZID are included.
    """
    print(as_hjson(bdb_path, compact))


def dump_full(bdb_path):
    """Dump all key-value pairs of any BerkeleyDB to stdout as HJSON."""

    def _sort_key(kv):
        """Place counters at top and sort them numerically."""
        k, v = kv
        m = re.search(r".*/c(\\d+)(/.*)$", k)
        if m:
            return 0, "{:04d}{}".format(int(m.group(1)), m.group(2))
        return 1, k

    with impl.nog_bdb.bdb_wrapper.Bdb(bdb_path) as bdb:
        # noinspection PyProtectedMember
        print(
            (
                hjson.dumps(
                    dict(bdb.bdb_dict),
                    sort_keys=True,
                    indent=2,
                    item_sort_key=_sort_key,
                )
            )
        )


def as_hjson(bdb_path, compact=True):
    """Get the state of a minter BerkeleyDB as HJSON.

    Only the fields used by EZID are included.
    """
    d = as_dict(bdb_path, compact)
    return hjson.dumps(d, indent=2)


def as_dict(bdb_path, compact=True):
    """Get the state of a minter BerkeleyDB as a dict.

    Only the fields used by EZID are included.
    """
    with impl.nog_bdb.bdb_wrapper.BdbWrapper(bdb_path, dry_run=False) as w:
        return w.as_dict(compact)


def open_bdb(bdb_path, is_new=False):
    """Open or create a BerkeleyDB file.

    All BerkeleyDB open or create operations in EZID should go through this function.

    Args:
        bdb_path (path):
        is_new (bool):
            False: Caller expects an existing path. Raise if path does not exist
            True: Caller expects a non-existing path. Raise if path already exists
    """

    def append_path(s):
        return '{}: {}'.format(s, bdb_path.as_posix())

    if is_new:
        if bdb_path.exists():
            raise impl.nog_sql.exc.MinterError(
                append_path('Unable to create new BerkeleyDB. Path already exists')
            )
        log.debug(append_path('Creating new BerkeleyDB'))
        impl.nog_sql.filesystem.create_missing_directories_for_file(bdb_path)
        flags_str = "c"
    else:
        if not bdb_path.exists():
            raise impl.nog_sql.exc.MinterError(append_path('Invalid BerkeleyDB path'))
        log.debug(append_path('Opening BerkeleyDB'))
        flags_str = "rw"
    try:
        return bsddb3.btopen(bdb_path.as_posix(), flags_str)
    except bsddb3.db.DBError as e:
        raise impl.nog_sql.exc.MinterError(
            '{}. error="{}"'.format(
                append_path('Unable to open BerkeleyDB file'), str(e)
            )
        )


def iter_bdb(root_path=None):
    """Yield paths to all the BerkeleyDB 'nog.bdb' minter database files in a
    minter directory hierarchy.

    Only databases files that are correctly placed in the hierarchy are returned, so
    the returned naan/prefix, slash and shoulder strings should always be valid.

    Yields: (naan/prefix, shoulder, Bdb), ...
    """

    bdb_root_path = get_bdb_root(root_path)
    for x in bdb_root_path.iterdir():
        if x.is_dir():
            for y in x.iterdir():
                if y.is_dir():
                    for z in y.iterdir():
                        if z.suffix == '.bdb':
                            bdb_path = _get_bdb_path(x.name, y.name, root_path)
                            with impl.nog_bdb.bdb_wrapper.Bdb(
                                bdb_path, dry_run=True
                            ) as bdb:
                                yield x.name, y.name, bdb


def get_path(ns, root_path=None, is_new=False):
    """Get the path to a BerkeleyDB minter file in a minter directory
    hierarchy.

    This is the only public method for determining the path to a minter. The main uses are:

    1) Generate a new path for a minter that is about to be created
    2) Return the path to an existing minter that was created in EZID
    3) Return the path to an existing minter that has been imported from N2T

    Basic validation to ensure that the identifiers match ARK and DOIs as used by EZID
    is performed. Case is significant, and upper case in an ARK or lower case in a DOI
    shoulder will cause validation to fail.

    Args:
        ns (str or IdNamespace): The full namespace of a shoulder.
            E.g., ark:/99999/fk4, doi:10.9111/FK4, doi:10.9111/

            For DOI shoulders, this is always the actual shoulder, not the shadow ark.

            Ending slash is significant and must be included if present in the minter
            namespace.

        is_new (bool or None):
            True: The caller intends to create a new minter at the given path. Causes the
                returned path to be checked to ensure that it's available, and causes any
                missing directories in the path to be created.
            False: The caller intends to open an existing minter at the returned path. Causes
                the returned path to be checked, to ensure that there is a minter available
                at the path.

        root_path (str or path, optional):
            Path to the root of the minter directory hierarchy. If not provided, the
            default for EZID is used. EZID's default path is read from the Django settings
            as specified by the DJANGO_SETTINGS_MODULE environment variable at startup.
    """

    # This performs basic validation of the DOI or ARK.
    ns = impl.nog_sql.id_ns.IdNamespace.from_str(ns)
    if is_new:
        if ns.scheme == 'doi':
            prefix_str = doi_prefix_to_naan(ns.naan_prefix)
            shoulder_str = ns.shoulder.lower() if ns.shoulder else None
        elif ns.scheme == 'ark':
            prefix_str, shoulder_str = ns.naan_prefix, ns.shoulder
        else:
            assert False, 'Internal error. ns="{}" is_new={}'.format(ns, is_new)
    else:
        prefix_str, shoulder_str = _get_existing_path(ns)

    bdb_path = pathlib.Path(
        get_bdb_root(root_path), prefix_str, shoulder_str or 'NULL', 'nog.bdb'
    ).resolve()

    if is_new:
        if bdb_path.exists():
            raise impl.nog_sql.exc.MinterPathError('Path already exists', bdb_path, ns)
        try:
            impl.nog_sql.filesystem.create_missing_directories_for_file(bdb_path)
        except IOError as e:
            raise impl.nog_sql.exc.MinterPathError(
                'Unable to create missing directories: {}'.format(str(e)), bdb_path, ns
            )
    else:
        if not bdb_path.exists():
            raise impl.nog_sql.exc.MinterError('Invalid BerkeleyDB path', bdb_path, ns)

    log.debug(
        'Resolved {} path. "{}" -> "{}"'.format(
            'new' if is_new else 'existing', str(ns), bdb_path.as_posix()
        ),
    )

    return bdb_path


def _get_existing_path(ns):
    # import ezidapp.models

    try:
        shoulder_model = ezidapp.models.shoulder.Shoulder.objects.get(prefix=str(ns))
    except ezidapp.models.shoulder.Shoulder.DoesNotExist:
        raise impl.nog_sql.exc.MinterPathError(
            'Unable to get path to minter: No matching prefix in Shoulder ORM',
            None,
            ns,
        )

    minter_uri = (shoulder_model.minter or '').strip()
    if not minter_uri:
        raise impl.nog_sql.exc.MinterPathError(
            'Unable to get path to minter: '
            'Matching prefix in Shoulder ORM does not specify a minter',
            None,
            ns,
        )

    minter_list = minter_uri.split('/')
    if len(minter_list) < 2:
        raise impl.nog_sql.exc.MinterPathError(
            'Unable to get path minter: '
            'Matching prefix in Shoulder ORM contains invalid minter str: {}'.format(
                minter_uri
            ),
            None,
            ns,
        )

    return minter_list[-2:]


def _get_bdb_path_by_namespace(ns, root_path=None):
    """Get the path to a BerkeleyDB minter file in a minter directory
    hierarchy.

    Use this only for generating a new path in which to create a minter BDB. For looking
    up the path to an existing minter, use get_bdb_path_by_shoulder_model().

    While this method should work for looking up existing minters created by EZID, the
    namespace alone does not always contain enough information for finding the path to a
    minter imported from N2T, which renders this method unsafe for use in the general
    case, where a minter may have been created either by EZID or N2T.

    If the namespace does not have a shoulder, the last directory in the returned path
    will be "NULL".

    Args:
        ns (str or IdNamespace): The full namespace of a shoulder.
            E.g., ark:/99999/fk4 or doi:10.9111/FK4
        root_path (str, optional):
            Path to the root of the minter directory hierarchy. If not provided, the
            default for EZID is used.

    Returns:
        pathlib.Path
    """
    ns = impl.nog_sql.id_ns.IdNamespace.from_str(ns)
    if ns.scheme == 'doi':
        naan_prefix_str = doi_prefix_to_naan(ns.naan_prefix)
    else:
        naan_prefix_str = ns.naan_prefix
    shoulder_str = ns.shoulder.lower() if ns.shoulder else 'NULL'
    return pathlib.Path(
        get_bdb_root(root_path),
        naan_prefix_str,
        shoulder_str,
        'nog.bdb',
    ).resolve()


def _get_bdb_path(naan_str, shoulder_str, root_path=None):
    """Get the path to a BerkeleyDB minter file in a minter directory
    hierarchy.

    The path may or may not exist.

    Args:
        naan_str (str): NAAN or Prefix of the minter to use. This must correspond to
            a directory name in the first level of the dir hierarchy in which the minter
            BerkeleyDBs are stored on disk. E.g., '99999'.
        shoulder_str (str): Shoulder of the minter to use. This must correspond to a
            directory name in the second level of the BerkeleyDB dir hierarchy. An empty
            shoulder value is treated as if it contains the string, "NULL".
        root_path (str, optional):
            Path to the root of the minter directory hierarchy. If not provided, the
            default for EZID is used.

    Returns:
        pathlib.Path
    """
    if not naan_str:
        raise impl.nog_sql.exc.MinterError('Invalid NAAN/Prefix: "{}"'.format(naan_str))
    if not shoulder_str:
        shoulder_str = 'NULL'
        log.debug('Replaced empty shoulder with the "NULL" string')
    root_path = get_bdb_root(root_path)
    minter_path = root_path.joinpath(naan_str, shoulder_str, "nog.bdb")
    return minter_path.resolve()


def get_bdb_path_by_shoulder_model(shoulder_model, root_path=None):
    """Get the path to a BerkeleyDB minter file in a minter directory
    hierarchy.

    The path may or may not exist. The caller may be obtaining the path in which to
    create a new minter, so the path is not checked.

    Args:
        shoulder_model (Shoulder): The Django ORM model for the shoulder to use for
            the minting. The model may be a legacy record for N2T based minting, or
            a record from a minter created in EZID.
        root_path (str, optional):
            Path to the root of the minter directory hierarchy. If not provided, the
            default for EZID is used.

    Returns:
        pathlib.Path
    """
    m = shoulder_model
    minter_uri = m.minter.strip()
    if not minter_uri:
        raise impl.nog_sql.exc.MinterNotSpecified(
            'A minter has not been specified (minter field in the database is empty)'
        )
    return pathlib.Path(
        get_bdb_root(root_path),
        '/'.join(minter_uri.split('/')[-2:]),
        'nog.bdb',
    ).resolve()


def get_bdb_root(root_path=None):
    """Get the root of the bdb minter hierarchy.

    This is a convenient stub for mocking out temp dirs during testing.
    """
    return pathlib.Path(root_path or django.conf.settings.MINTERS_PATH)


def doi_prefix_to_naan(prefix_str, allow_lossy=False):
    """Convert the number after "10." in a DOI to a 1 letter + 4 digit string.
    E.g.: doi:10.5072/D9 -> 5072 -> b5072

    Should give same output as N2T doip2naan.d2n(

    Args:
        prefix_str (str, int): The number after "10." and before the slash in a DOI.
            E.g., 123 from doi:10.123/X.
        allow_lossy (bool): N2T doip2naan does not allow lossy conversions, and
            returns the original DOI if the prefix > 99999. When this flag is set to
            True, this function behaves in the same way.
    """
    n = int(prefix_str)
    last4_str = '{:04d}'.format(n)[-4:]
    if n < 10 ** 5:
        return 'bcdfghjkmn'[n // 10 ** 4] + last4_str
    if n < 10 ** 6:
        if allow_lossy:
            return ' pqrstvwxz'[n // 10 ** 5] + last4_str
        raise OverflowError('"{}" requires a lossy conversion'.format(prefix_str))
    raise OverflowError('"{}" is out of range'.format(prefix_str))


def doi_to_shadow_ark(doi_str, allow_lossy=False):
    """Convert DOI to a 'shadow ARK'.

    Should give the same results as the N2T doip2naan command line
    program.
    """
    doi_ns = impl.nog_sql.id_ns.IdNamespace.from_str(doi_str)
    assert doi_ns.scheme == 'doi', 'Expected a complete DOI, not "{}"'.format(doi_str)
    try:
        ark_naan = doi_prefix_to_naan(doi_ns.naan_prefix, allow_lossy)
    except OverflowError as e:
        raise impl.nog_sql.exc.MinterError('Unable to create shadow ark: {}'.format(str(e)))
    ark_ns = impl.nog_sql.id_ns.IdNamespace(
        'ark', ark_naan, doi_ns.slash, (doi_ns.shoulder or '').lower()
    )
    return str(ark_ns)


def create_bdb_from_hjson(bdb_path, hjson_str):
    """Create a new BerkeleyDB database file from JSON or HJSON.

    Args:
        bdb_path (path): Absolute path to location of new BerkeleyDB file. Any
            missing directories in the path are created. The path must not already
            exist.
        hjson_str (JSON or HJSON str): The minter database to create.
    """
    bdb_dict = hjson.loads(hjson_str)
    create_bdb_from_dict(bdb_path, bdb_dict)


def create_bdb_from_dict(bdb_path, bdb_dict):
    bdb_path = pathlib.Path(bdb_path)
    if bdb_path.exists():
        raise impl.nog_sql.exc.MinterError(
            'Path already exists: {}'.format(bdb_path.as_posix())
        )
    impl.nog_sql.filesystem.create_missing_directories_for_file(bdb_path)
    bdb = bsddb3.btopen(bdb_path.as_posix(), 'c')
    bdb.update({bytes(k): bytes(v) for k, v in list(bdb_dict.items())})
    bdb.close()
