"""Mint one or more new identifiers on an existing shoulder
"""
import argparse
import logging

import django.core.management

import ezidapp.models
import impl.nog.util
import nog.minter

log = logging.getLogger(__name__)


class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()

    def add_arguments(self, parser):
        parser.add_argument(
            'shoulder_str',
            metavar='shoulder',
            help="Full ARK or DOI shoulder. E.g., ark:/99999/fk4 or doi:10.9111/FK4",
        )
        parser.add_argument(
            "--count",
            "-c",
            metavar="mint-count",
            type=int,
            default=1,
            help="Number of identifiers to mint",
        )
        parser.add_argument(
            "--update",
            "-u",
            action="store_true",
            help="""After minting, update the starting point of the minter to the next
            new identifier. Without --update, minting does not interfere with the
            sequence of identifiers that the minter will yield in regular use.""",
        )
        parser.add_argument(
            "--debug", action="store_true", help="Debug level logging",
        )

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog.util.log_to_console(__name__, opt.debug)

        try:
            shoulder_model = ezidapp.models.Shoulder.objects.get(
                prefix=opt.shoulder_str
            )
        except ezidapp.models.Shoulder.DoesNotExist:
            raise django.core.management.CommandError(
                'Invalid shoulder: {}'.format(opt.shoulder_str)
            )

        for i, id_str in enumerate(
            nog.minter.mint_ids(shoulder_model, opt.count, not opt.update)
        ):
            log.info("{: 5d} {}".format(i + 1, id_str))
