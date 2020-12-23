"""BerkeleyDB utilities.

These utilities work directly with the BerkeleyDB (.bdb) files on disk. They do not
connect to the EZID database.

- list: List basic information about the minters found in the directory tree rooted at
  the default location or under another location if '--root' is specified.

  E.g.: ./manage.py bdb list

- unique: List the unique values and the number of occurrences of each value for a
  single minter field.

  E.g.: ./manage.py bdb unique --field oacounter

- backup: Copy a minter to backup location. This, together with 'restore' is intended to
  provide an easy way to run repeatable tests or experiments.

  E.g.: ./manage.py bdb backup ark:/99999/fk4

- restore: Copy a minter from a backup created with 'backup' to its original location.
  Does not remove the backup file, so can be used any number of times to roll the minter
  back to a known state.

  E.g.: ./manage.py bdb restore ark:/99999/fk4

- dump: Dump a minter to a normalized HJSON file.

  E.g.: ./manage.py bdb dump ark:/99999/fk4

- dump-full: Dump arbitrary BerkeleyDB to HJSON.

  E.g.: ./manage.py bdb dump-full path/to/database.xyz

- create: Create a new minter for a given shoulder.

  E.g.: ./manage.py bdb create doi:10.1234/fk4

- mint: Mint any number of identifiers with a given minter. By default, the minter state
  is not updated to reflect the minted identifiers, so the result can be considered as
  a "preview" of the identifiers the minter will yield when next used by EZID.

  This command is intended mainly for testing an existing minter and only provides
  identifiers going forward from the minter's current state. See also: 'slice'

  E.g.: ./manage.py bdb mint doi:10.123/fk4 --update

- slice: Mint a "slice" of identifiers with a minter that is created on the fly and
  destroyed after minting.

  A slice is sequence of identifiers starting after some number of identifiers have
  already been minted, and containing a fixed number of identifiers, such as 10
  identifiers starting after 1 million identifiers have been minted.

  This command intended for generating a sequence expected from a given minter in order
  to determine when and where identifiers found 'in the wild' would have been minted.
"""


import argparse
import logging
import shutil
import sys
import tempfile

import django.conf
import django.core.management
import pathlib2

import impl.nog.filesystem
import impl.nog.util
import nog.bdb
import nog.exc
import nog.id_ns
import nog.minter

log = logging.getLogger(__name__)


class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.bdb_path = None
        self.opt = None

    def add_arguments(self, parser):
        parser.formatter_class = argparse.RawDescriptionHelpFormatter
        parser.add_argument(
            "action_str",
            choices=(
                'list',
                'unique',
                'backup',
                'restore',
                'dump',
                'dump-full',
                'mint',
                'create',
                'slice',
            ),
        )
        parser.add_argument(
            "ns_str", metavar="identifier", nargs='?', help='Full ARK or DOI identifier'
        )
        parser.add_argument(
            "--path", type=pathlib2.Path, metavar="path", help="Path to BerkeleyDB file"
        )
        parser.add_argument(
            "--root",
            dest="root_path",
            metavar="path",
            help="Override default root path for BerkeleyDB minters",
        )
        # For 'mint'
        parser.add_argument(
            "--update",
            "-u",
            action="store_true",
            help="""For use with 'mint': After minting, update the starting point of the
            minter to the next new identifier. Without this switch, minting only
            provides a 'preview' of the sequence of identifiers that the minter will
            yield in regular use""",
        )
        parser.add_argument(
            "--start",
            "-s",
            type=int,
            default=0,
            help="""For use with 'slice': Suppress initial identifiers. The minter has
            to always start at zero, but this argument makes it appear as if the minter
            was started directly at some point later in the sequence. If 'start' is a large
            number, there will be a delay while the minter works through the suppressed
            identifiers""",
        )
        parser.add_argument(
            "--count",
            "-c",
            type=int,
            default=1,
            help="For use with 'mint' and 'slice': Set the number of identifiers to mint",
        )
        # For 'unique'
        parser.add_argument(
            "--field",
            "-f",
            help="For use with 'unique': Set the minter field to use. E.g., 'oacounter'",
        )
        # For 'create'
        parser.add_argument(
            '--clobber',
            '-b',
            action='store_true',
            help="""For use with 'create': Overwrite any minter (or other file) that
            exists at the path required by he minter being created""",
        ),
        parser.add_argument(
            "--debug", action="store_true", help="Debug level logging",
        )

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog.util.log_to_console(__name__, opt.debug)

        # 'list' is a reserved keyword.
        if opt.action_str == 'list':
            opt.action_str = 'list_bdb'
        opt.action_str = opt.action_str.replace('-', '_')

        if self.opt.ns_str is not None:
            self.bdb_path = self._get_dbd_path(is_new=False)

        # src_path = impl.nog.filesystem.abs_path(
        #     "./test_docs/{}_{}.bdb".format(ns_str, shoulder_str)
        # )
        # dst_path = os.path.join(
        #     django.conf.settings.MINTERS_PATH, ns_str, shoulder_str, "nog.bdb",
        # )

        try:
            return getattr(self, opt.action_str)()
        except nog.exc.MinterError as e:
            raise django.core.management.CommandError('Minter error: {}'.format(str(e)))

    # See the docstring for descriptions of the actions.

    def list_bdb(self):
        root_path = nog.bdb._get_bdb_root(self.opt.root_path)
        if not root_path.is_dir():
            raise django.core.management.CommandError(
                'Invalid root path: {}'.format(root_path.as_posix())
            )
        log.info("Listing minters below root: {}".format(root_path))
        for i, (naan_prefix_str, shoulder_str, bdb) in enumerate(
            nog.bdb.iter_bdb(self.opt.root_path)
        ):
            log.info(
                'index: {:<4d} naan_or_prefix: {:<6} shoulder: {:<12} '
                'template: {:<20} oacounter: {:<10,d} oatop: {:<10,d}'.format(
                    i,
                    naan_prefix_str,
                    shoulder_str,
                    bdb.get("template"),
                    bdb.get_int("oacounter"),
                    bdb.get_int("oatop"),
                )
            )

    def unique(self):
        root_path = nog.bdb._get_bdb_root(self.opt.root_path)
        if not root_path.is_dir():
            raise django.core.management.CommandError(
                'Invalid root path: {}'.format(root_path.as_posix())
            )
        if not self.opt.field:
            raise django.core.management.CommandError(
                'The --field parameter is required for this command'
            )
        log.info("Finding unique values for field: {}".format(self.opt.field))
        count_dict = {}
        for i, (naan_prefix_str, shoulder_str, bdb) in enumerate(
            nog.bdb.iter_bdb(self.opt.root_path)
        ):
            try:
                k = bdb.get(self.opt.field)
            except KeyError:
                k = '<field not in minter>'
            count_dict.setdefault(k, 0)
            count_dict[k] += 1

        for field_str, count_int in sorted(list(count_dict.items()), key=lambda x: x[1]):
            log.info(
                'Number of minters with this value: {:<6,d} value: {}'.format(
                    count_int, field_str
                )
            )

    def backup(self):
        self._assert_bdb_path(exists=True)
        src_path = self._get_dbd_path(is_new=False)
        dst_path = self._get_bdb_backup_path()
        self._copy_file(src_path, dst_path)

    def restore(self):
        self._assert_bdb_path(exists=True)
        src_path = self._get_dbd_path(is_new=False)
        dst_path = self._get_bdb_backup_path()
        self._copy_file(dst_path, src_path)

    def dump(self):
        self._assert_bdb_path(exists=True)
        print("Dumping minter state to HJSON", file=sys.stderr)
        nog.bdb.dump(self.bdb_path)

    def dump_full(self):
        self._assert_bdb_path(exists=True)
        print("Dumping arbitrary BerkeleyDB to HJSON", file=sys.stderr)
        nog.bdb.dump_full(self.bdb_path)

    def mint(self):
        self._assert_bdb_path(exists=True)
        for i, id_str in enumerate(
            nog.minter.mint_by_bdb_path(
                self.bdb_path, self.opt.count, dry_run=not self.opt.update,
            )
        ):
            log.info("{: 5d}: {}".format(i + 1, id_str))

    def create(self):
        self._assert_bdb_path(exists=None if self.opt.clobber else False)
        if self.bdb_path.exists() and self.opt.clobber:
            log.info('Overwriting existing file')
            self.bdb_path.unlink()
        # full_shoulder_str = '/'.join([self.opt.ns_str.naan_prefix, self.opt.ns_str.shoulder])
        bdb_path = nog.minter.create_minter_database(
            self.opt.ns_str, self.opt.root_path
        )
        log.info('Created minter for: {}'.format(bdb_path))

    def slice(self):
        case_fn = str.upper if self.opt.ns_str.startswith('doi:') else str.lower
        dir_path = pathlib2.Path(tempfile.mkdtemp())
        try:
            bdb_path = nog.minter.create_minter_database(
                self.opt.ns_str, dir_path.as_posix()
            )
            for i, id_str in enumerate(
                nog.minter.mint_by_bdb_path(
                    bdb_path, self.opt.count, dry_run=True,
                )
            ):
                # noinspection PyArgumentList
                # log.info("{}".format(case_fn(self.opt.ns_str + id_str)))
                print(case_fn(self.opt.ns_str + id_str))
        finally:
            shutil.rmtree(dir_path.as_posix())

    def _assert_bdb_path(self, exists=None):
        if not self.bdb_path:
            raise django.core.management.CommandError(
                'NAAN/Prefix and Shoulder, OR path to a BDB file is required for this '
                'command'
            )
        if exists is None:
            return
        elif exists is True and not self.bdb_path.exists():
            raise django.core.management.CommandError(
                'Path does not exist: {}'.format(self.bdb_path)
            )
        elif exists is False and self.bdb_path.exists():
            raise django.core.management.base.CommandError(
                'Path already exists. Use --clobber to overwrite: {}'.format(
                    self.bdb_path
                )
            )

    def _get_dbd_path(self, is_new):
        try:
            id_ns = nog.id_ns.IdNamespace.from_str(self.opt.ns_str)
        except nog.exc.MinterError:
            log.info(
                'Argument is not a DOI or ARK. Using it as path: {}'.format(
                    self.opt.ns_str
                )
            )
            return pathlib2.Path(self.opt.ns_str)
        else:
            p = nog.bdb.get_path(id_ns, self.opt.root_path, is_new)
            log.info('Resolved namespace to path.')
            log.info('Namespace: {}'.format(self.opt.ns_str))
            log.info('Path: {}'.format(p))
            return p

    def _copy_file(self, src_path, dst_path):
        impl.nog.filesystem.create_missing_directories_for_file(dst_path)
        log.info('Copied: {}'.format(src_path))
        log.info('     -> {}'.format(dst_path))
        shutil.copy(src_path.as_posix(), dst_path.as_posix())

    def _get_bdb_backup_path(self):
        return pathlib2.Path(django.conf.settings.MINTERS_PATH).parent.joinpath(
            'minter_backups', self.bdb_path.with_suffix('.backup.bdb'),
        )
