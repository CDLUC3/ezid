#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Minter utilities

- list: List basic information about the minters.

  E.g.: ./manage.py diag-minter list

- unique: List the unique values and the number of occurrences of each value for a
  single minter field.

  E.g.: ./manage.py diag-minter unique --field oacounter


- dump: Dump a minter to a normalized JSON file.

  E.g.: ./manage.py diag-minter dump ark:/99999/fk4

- dump-full: Dump all minters to a JSON file.

  E.g.: ./manage.py diag-minter dump-full path/to/minters.json


- mint: Mint any number of identifiers with a given minter. By default, the minter state
  is not updated to reflect the minted identifiers, so the result can be considered as
  a "preview" of the identifiers the minter will yield when next used by EZID.

  This command is intended mainly for testing an existing minter and only provides
  identifiers going forward from the minter's current state. See also: 'slice'

  E.g.: ./manage.py diag-minter mint doi:10.123/fk4 --count 2 --update

  Note: this is equivalent to the 'shoulder-mint' command:
  ./manage.py shoulder-mint doi:10.123/fk4 --count 2 --update

- forward: "Fast forward" all minters by a given count. By default, the minter state
  is not updated to reflect the minted identifiers, so the result can be considered as
  a "preview" of the identifiers the minter will yield when next used by EZID.

  Similar to the 'mint',  this command  is intended mainly for testing existing minters 
  and only provides identifiers going forward from the minter's current state.

  E.g.: ./manage.py diag-minter forward --count 2 --update

- slice: Mint a "slice" of identifiers with a minter that is created on the fly and
  destroyed after minting. NOT YET implemented for MySQL version minter.

  A slice is sequence of identifiers starting after some number of identifiers have
  already been minted, and containing a fixed number of identifiers, such as 10
  identifiers starting after 1 million identifiers have been minted.

  This command intended for generating a sequence expected from a given minter in order
  to determine when and where identifiers found 'in the wild' would have been minted.
"""


import argparse
import logging

import django.conf
import django.core.management
import django.core.management.base

import ezidapp.models.minter
import impl.nog_sql.exc
import impl.nog_sql.filesystem
import impl.nog_sql.id_ns
import impl.nog_sql.ezid_minter
import impl.nog_sql.util

log = logging.getLogger(__name__)


class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.opt = None

    def create_parser(self, *args, **kwargs):
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = argparse.RawTextHelpFormatter
        return parser

    def add_arguments(self, parser):
        parser.add_argument(
            "action_str",
            choices=(
                'list',
                'unique',
                'dump',
                'dump-full',
                'mint',
                'forward',
            ),
        )
        parser.add_argument(
            "prefix", metavar="prefix", nargs='?', help='Full prefix/shoulder. E.g., ark:/99999/fk4'
        )
        # For 'mint' and forward
        parser.add_argument(
            "--update",
            "-u",
            action="store_true",
            help="""For use with 'mint' and 'forward': After minting, update the starting point of the
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
            help="For use with 'mint', 'forward' and 'slice': Set the number of identifiers to mint",
        )
        # For 'unique'
        parser.add_argument(
            "--field",
            "-f",
            help="For use with 'unique': Set the minter field to use. E.g., 'oacounter'",
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Debug level logging",
        )

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog_sql.util.log_setup(__name__, opt.debug)

        # 'list' is a reserved keyword.
        if opt.action_str == 'list':
            opt.action_str = 'list_minter'
        opt.action_str = opt.action_str.replace('-', '_')

        self.id_str = 'identifer'
        if self.opt.count> 1:
            self.id_str = f'{self.id_str}s'
        
        update_str = 'update minter state after minting'
        if self.opt.update:
            self.update_str = f'and {update_str}'
        else:
            self.update_str =  f'without {update_str}'

        try:
            return getattr(self, opt.action_str)()
        except impl.nog_sql.exc.MinterError as e:
            raise django.core.management.CommandError('Minter error: {}'.format(str(e)))

    # See the docstring for descriptions of the actions.

    def list_minter(self):
        log.info("Listing minters ...")
        i = 0
        for minter in ezidapp.models.minter.Minter.objects.all().order_by('prefix'):
            prefix = minter.prefix
            template =  minter.minterState.get("template")
            oacounter =  minter.minterState.get("oacounter")
            oatop =  minter.minterState.get("oatop")

            log.info(
                'index: {:<4d} prefix: {:<6} '
                'template: {:<20} oacounter: {:<10} oatop: {:<10}'.format(
                    i,
                    prefix,
                    template,
                    oacounter,
                    oatop,
                )
            )
            i += 1

    def unique(self):
        if not self.opt.field:
            raise django.core.management.CommandError(
                'The --field parameter is required for this command'
            )
        log.info("Finding unique values for field: {}".format(self.opt.field))
        count_dict = {}
        for minter in ezidapp.models.minter.Minter.objects.all().order_by('prefix'):
            try:
                k = minter.minterState.get(self.opt.field)
            except KeyError:
                k = '<field not in minter>'
            count_dict.setdefault(k, 0)
            count_dict[k] += 1

        for field_str, count_int in sorted(count_dict.items(), key=lambda x: x[1]):
            log.info(
                'Number of minters with this value: {:<6,d} value: {}'.format(count_int, field_str)
            )

    def dump(self):
        if self.opt.prefix is None:
            raise django.core.management.CommandError(
                'A prefix is required for this command'
            )
        try:
            minter = ezidapp.models.minter.Minter.objects.get(prefix=self.opt.prefix)
            print(minter.minterState)
        except Exception as ex:
            print(f"Minter error: {ex} - Searched prefix: {self.opt.prefix}")
    
    def dump_full(self):
        for minter in ezidapp.models.minter.Minter.objects.all().order_by('prefix'):
            print(minter.minterState)

    def mint(self):
        if self.opt.prefix is None:
            raise django.core.management.CommandError(
                'A prefix is required for this command'
            )
  
        log.info(f"Mint {self.opt.count} {self.id_str} on minter {self.opt.prefix} {self.update_str}")

        for i, id_str in enumerate(
            impl.nog_sql.ezid_minter.mint_by_prefix(
                self.opt.prefix,
                self.opt.count,
                dry_run=not self.opt.update,
            )
        ):
            log.info("{: 5d}: {}".format(i + 1, id_str))

    def forward(self):
        for minter in ezidapp.models.minter.Minter.objects.all().order_by('prefix'):
            prefix = minter.prefix
            log.info(f"Fast-Forwarding minter {prefix} by {self.opt.count} {self.update_str}")
            id_str = '<start>' 

            for i, id_str in enumerate(
                impl.nog_sql.ezid_minter.mint_by_prefix(
                    prefix,
                    self.opt.count,
                    dry_run=not self.opt.update,
                )
            ):
                log.info("{: 5d}: {}".format(i + 1, id_str))


