"""List existing shoulders."""
import ezidapp.models.update_queue
import argparse
import logging

import django.core.management

import impl.nog.shoulder
import impl.nog.util

log = logging.getLogger(__name__)


class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()

    def add_arguments(self, parser):
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Debug level logging",
        )

    # noinspection PyAttributeOutsideInit
    def handle(self, *_, **opt):
        for r in ezidapp.models.update_queue.UpdateQueue.objects.all().order_by("seq"):
            print(repr(r))
            print(r.object)
            # print(str(r.))
            # pass

        # self.opt = opt = argparse.Namespace(**opt)
        # impl.nog.util.log_setup(__name__, opt.debug)
        #
        # impl.nog.shoulder.dump_shoulders()
