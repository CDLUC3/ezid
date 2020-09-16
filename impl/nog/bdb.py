"""Minter BerkeleyDB related utilities
"""

from __future__ import absolute_import, division, print_function

import logging
import re

import django.core
import django.db
import hjson
import pathlib2

import impl.nog.filesystem
import nog.bdb_wrapper

try:
    import bsddb
except ImportError:
    # noinspection PyUnresolvedReferences
    import bsddb3 as bsddb

import django.conf
import impl.nog.filesystem
import nog.exc
import nog.id_ns

log = logging.getLogger(__name__)


MINTER_TEMPLATE_PATH = impl.nog.filesystem.abs_path("../../etc/minter_template.hjson")


def dump_by_ns(ns, root_path=None, compact=True):
    bdb_path = get_bdb_path_by_namespace(ns, root_path)
    return dump(bdb_path, compact)


def as_hjson_by_shoulder(ns, root_path=None, compact=True):
    bdb_path = get_bdb_path_by_namespace(ns, root_path)
    return as_hjson(bdb_path, compact)


def as_dict_by_shoulder(ns, root_path=None, compact=True):
    bdb_path = get_bdb_path_by_namespace(ns, root_path)
    return as_dict(bdb_path, compact)


def dump(bdb_path, compact=True):
    """Dump the state of a minter BerkeleyDB to stdout as HJSON. Only the fields used by EZID
    are included.
    """
    log.info(as_hjson(bdb_path, compact))


def dump_full(bdb_path):
    """Dump all key-value pairs of any BerkeleyDB to stdout as HJSON.
    """

    def _sort_key(kv):
        """Place counters at top and sort them numerically"""
        k, v = kv
        m = re.search(r".*/c(\d+)(/.*)$", k)
        if m:
            return 0, "{:04d}{}".format(int(m.group(1)), m.group(2))
        return 1, k

    with nog.bdb_wrapper.Bdb(bdb_path) as bdb:
        print(
            hjson.dumps(
                dict(bdb._bdb_dict), sort_keys=True, indent=2, item_sort_key=_sort_key
            )
        )


def as_hjson(bdb_path, compact=True):
    """Get the state of a minter BerkeleyDB as HJSON. Only the fields used by EZID are
    included.
    """
    d = as_dict(bdb_path, compact)
    return hjson.dumps(d, indent=2)


def as_dict(bdb_path, compact=True):
    """Get the state of a minter BerkeleyDB as a dict. Only the fields used by EZID are
    included.
    """
    with nog.bdb_wrapper.BdbWrapper(bdb_path, dry_run=False) as w:
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
            raise nog.exc.MinterError(
                append_path('Unable to create new BerkeleyDB. Path already exists')
            )
        log.debug(append_path('Creating new BerkeleyDB'))
        impl.nog.filesystem.create_missing_directories_for_file(bdb_path)
        flags_str = "c"
    else:
        if not bdb_path.exists():
            raise nog.exc.MinterError(append_path('Invalid BerkeleyDB path'))
        log.debug(append_path('Opening BerkeleyDB'))
        flags_str = "rw"
    try:
        return bsddb.btopen(bdb_path.as_posix(), flags_str)
    except bsddb.db.DBError as e:
        raise nog.exc.MinterError(
            '{}. error="{}"'.format(append_path('Unable to open BerkeleyDB file'), str(e))
        )


def get_bdb_path(naan_str, shoulder_str, root_path=None):
    """Get the path to a BerkeleyDB minter file in a minter directory hierarchy.

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
        pathlib2.Path
    """
    if not naan_str:
        raise impl.nog.exc.MinterError('Invalid NAAN/Prefix: "{}"'.format(naan_str))
    if not shoulder_str:
        shoulder_str = 'NULL'
        log.debug('Replaced empty shoulder with the "NULL" string')
    root_path = get_bdb_root(root_path)
    minter_path = root_path.joinpath(naan_str, shoulder_str, "nog.bdb")
    return minter_path.resolve()


def get_bdb_path_by_namespace(ns, root_path=None):
    """Get the path to a BerkeleyDB minter file in a minter directory hierarchy.

    The path may or may not exist.

    Args:
        ns (str or IdNamespace): The full namespace of a shoulder.
            E.g., ark:/99999/fk4 or doi:10.9111/FK4
        root_path (str, optional):
            Path to the root of the minter directory hierarchy. If not provided, the
            default for EZID is used.

    Returns:
        pathlib2.Path
    """
    ns = nog.id_ns.split_namespace(ns)
    if ns.scheme_sep == 'doi:10.':
        naan_prefix_str = doi_prefix_to_naan(ns.naan_prefix)
    else:
        naan_prefix_str = ns.naan_prefix
    return pathlib2.Path(
        get_bdb_root(root_path),
        naan_prefix_str,
        ns.shoulder.lower() if ns.shoulder else 'NULL',
        'nog.bdb',
    ).resolve()


def get_bdb_root(root_path=None):
    """Get the root of the bdb minter hierarchy. This is a convenient stub for
    mocking out temp dirs during testing.
    """
    return pathlib2.Path(root_path or django.conf.settings.MINTERS_PATH)


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
                            bdb_path = get_bdb_path(x.name, y.name, root_path)
                            with nog.bdb_wrapper.Bdb(bdb_path, dry_run=True) as bdb:
                                yield x.name, y.name, bdb


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
    """Convert DOI to a 'shadow ARK'. Should give the same results as the N2T doip2naan
    command line program.
    """
    doi_ns = nog.id_ns.split_doi_namespace(doi_str)
    try:
        ark_naan = doi_prefix_to_naan(doi_ns.naan_prefix, allow_lossy)
    except OverflowError as e:
        raise nog.exc.MinterError('Unable to create shadow ark: {}'.format(str(e)))
    ark_ns = nog.id_ns.IdNamespace(
        'ark:/', ark_naan, doi_ns.slash, doi_ns.shoulder.lower()
    )
    return str(ark_ns)


def create_minter_database(shoulder_ns, root_path=None):
    """Create a new BerkeleyDB file.

    Args:
        shoulder_ns: DOI or ARK shoulder namespace
        root_path:

    Returns (path): Absolute path to the new nog.bdb file.
    """
    shoulder_ns = nog.id_ns.split_namespace(shoulder_ns)
    bdb_path = get_bdb_path_by_namespace(shoulder_ns, root_path)

    with open(MINTER_TEMPLATE_PATH) as f:
        template_str = f.read()

    template_str = template_str.replace("$NAAN$", shoulder_ns.naan_prefix)
    template_str = template_str.replace("$PREFIX$", shoulder_ns.shoulder)

    minter_dict = hjson.loads(template_str)
    d = {bytes(k): bytes(v) for k, v in minter_dict.items()}

    bdb = None
    try:
        bdb = open_bdb(bdb_path, is_new=True)
        bdb.clear()
        bdb.update(d)
    finally:
        if bdb:
            bdb.close()

    return bdb_path


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
    bdb_path = pathlib2.Path(bdb_path)
    if bdb_path.exists():
        raise nog.exc.MinterError('Path already exists: {}'.format(bdb_path.as_posix()))
    impl.nog.filesystem.create_missing_directories_for_file(bdb_path)
    bdb = bsddb.btopen(bdb_path.as_posix(), 'c')
    bdb.update({bytes(k): bytes(v) for k, v in bdb_dict.items()})
    bdb.close()
