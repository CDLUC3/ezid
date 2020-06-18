"""Create a new shoulder
"""

from __future__ import absolute_import, division, print_function

import datetime
import logging

import django.core.management.base
import hjson
import impl.nog_minter
import utils.filesystem
import ezidapp.models
import config

try:
    import bsddb
except ImportError:
    import bsddb3 as bsddb

import django.contrib.auth.models
import django.core.management.base
import django.db.transaction

FILE_PROTOCOL = "file://"

log = logging.getLogger(__name__)


class Command(django.core.management.base.BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("naan_str", metavar="naan")
        parser.add_argument("shoulder_str", metavar="shoulder")
        parser.add_argument("name_str", metavar="name")
        parser.add_argument(
            "--debug", "-g", action="store_true", help="Debug level logging",
        )

    def handle(self, *_, **opt):
        naan_str = opt["naan_str"]
        shoulder_str = opt["shoulder_str"]
        name_str = opt["name_str"]

        # self.assert_valid_name(name_str)

        self.add_shoulder_file_record(naan_str, shoulder_str, name_str)
        self.add_shoulder_db_record(naan_str, shoulder_str, name_str)
        self.create_minter_database(naan_str, shoulder_str)

        print("\nShoulder created. Restart the EZID service to activate.")

    def assert_valid_name(self, name_str):
        name_set = [x.name for x in ezidapp.models.Shoulder.objects.all()]

        if name_str not in name_set:
            print("Name must be one of:")
            for s in sorted(name_set):
                print(u"  {}".format(s))
            raise django.core.management.base.CommandError(
                "Invalid name: {}".format(name_str)
            )

    def add_shoulder_file_record(self, naan_str, shoulder_str, name_str):
        """Add a new shoulder entry to the master shoulders file"""
        _url = config.get("shoulders.url")

        assert _url.startswith(FILE_PROTOCOL)

        file_path = _url[len(FILE_PROTOCOL) :]
        now = datetime.datetime.now()

        with open(file_path, "a") as f:
            f.write(":: ark:/{}/{}\n".format(naan_str, shoulder_str))
            f.write("type: shoulder\n")
            f.write("manager: ezid\n")
            f.write("name: {}\n".format(name_str))
            f.write("date: {:04d}.{:02d}.{:02d}\n".format(now.year, now.month, now.day))
            f.write("minter: https://deprecated.org/remove/later\n")
            f.write("\n")

    def add_shoulder_db_record(self, naan_str, shoulder_str, name_str):
        """Add a new shoulder row to the shoulder table"""
        ezidapp.models.Shoulder.objects.create(
            prefix="ark:/{}/{}".format(naan_str, shoulder_str),
            type="ARK",
            name=name_str,
            minter="https://deprecated.org/remove/later",
            datacenter=None,
            crossrefEnabled=False,
            isTest=False,
        )

    def create_minter_database(self, naan_str, shoulder_str):
        """Create a new BerkeleyDB minter database"""
        template_path = utils.filesystem.abs_path("./resources/minter_template.hjson")
        with open(template_path) as f:
            template_str = f.read()

        template_str.replace("$NAAN$", naan_str)
        template_str.replace("$PREFIX$", shoulder_str)

        minter_dict = hjson.loads(template_str)
        d = {bytes(k): bytes(v) for k, v in minter_dict.items()}

        bdb = impl.nog_minter.open_bdb(
            naan_str, shoulder_str, root_path=None, flags_str="c"
        )
        bdb.clear()
        bdb.update(d)

    def dump_shoulders(self):
        for x in ezidapp.models.Shoulder.objects.all():
            print(x)
