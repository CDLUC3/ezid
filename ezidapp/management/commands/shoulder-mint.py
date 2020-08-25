"""Mint one or more new identifiers on an existing shoulder
"""
import argparse
import logging

import django.core.management.base

import ezidapp.models
import impl.nog_minter

log = logging.getLogger(__name__)


class Command(django.core.management.base.BaseCommand):
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
            "--preview",
            "-p",
            action="store_true",
            help="""Do not update the minter state (BerkeleyDB). This causes the minter
            to yield the same sequence of identifier(s) the next time it is used""",
        )
        parser.add_argument(
            "--debug", action="store_true", help="Debug level logging",
        )

    def handle(self, *_, **opt):
        opt = argparse.Namespace(**opt)

        if opt.debug:
            logging.getLogger('').setLevel(logging.DEBUG)

        try:
            shoulder_model = ezidapp.models.Shoulder.objects.get(
                prefix=opt.shoulder_str
            )
        except ezidapp.models.Shoulder.DoesNotExist:
            raise django.core.management.CommandError(
                'Invalid shoulder: {}'.format(opt.shoulder_str)
            )

        for i, id_str in enumerate(
            impl.nog_minter.mint_identifier_gen(shoulder_model, opt.count, opt.preview)
        ):
            print("{: 5d} {}".format(i + 1, id_str))
