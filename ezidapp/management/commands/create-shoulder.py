"""Create a new shoulder
"""

from __future__ import absolute_import, division, print_function

import datetime
import logging
import re

import django.core.management
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
import impl.util

FILE_PROTOCOL = "file://"

log = logging.getLogger(__name__)


class Command(django.core.management.base.BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("naan_str", metavar="naan")
        parser.add_argument("shoulder_str", metavar="shoulder")
        parser.add_argument("name_str", metavar="name")
        parser.add_argument(
            "--doi",
            "-d",
            action="store_true",
            help="Create a DOI minter (ARK is created by default)",
        )
        parser.add_argument(
            "--debug", "-g", action="store_true", help="Debug level logging",
        )

    def handle(self, *_, **opt):
        # - NAAN: Registered part of prefix. E.g., ARK: `77913`, DOI: `b7913`
        # - Shoulder: User part of prefix. E.g., `r7`
        # - NOID: NAAN / Shoulder. E.g., '77913/r7'
        # - Prefix: Minter protocol + NOID. E.g., 'doi:10.77913/r7'

        naan_str = opt["naan_str"]
        shoulder_str = opt["shoulder_str"]
        name_str = opt["name_str"]
        is_doi = opt["doi"]

        if is_doi:
            shadow_str = impl.util.doi2shadow(
                "10.{}/{}".format(naan_str, shoulder_str.upper())
            )
            naan_str, shoulder_str = shadow_str.split("/")
            noid_str = "/".join([naan_str, shoulder_str])
            prefix_str = "doi:10.{}".format(noid_str)
            if not re.match(r"[a-z0-9]\d{4}$", naan_str):
                raise django.core.management.CommandError(
                    "NAAN for a DOI must be 5 digits, or one lower case character "
                    "and 4 digits:".format(naan_str)
                )
        else:
            noid_str = "/".join([naan_str, shoulder_str])
            prefix_str = "ark:/{}".format(noid_str)
            if not re.match(r"\d{5}$", naan_str):
                raise django.core.management.CommandError(
                    "NAAN for an ARK must be 5 digits:".format(naan_str)
                )

        # print('naan_str=' + naan_str)
        # print('noid_str=' + noid_str)
        # print('prefix_str=' + prefix_str)
        # print(re.split(r'[/:.]', prefix_str)[-2:])
        # return

        print(
            'Creating {} minter for NAAN "{}" with shoulder "{}", prefix "{}"...'.format(
                "a DOI" if is_doi else "an ARK", naan_str, shoulder_str, prefix_str
            )
        )

        try:
            self.add_shoulder_db_record(noid_str, prefix_str, name_str, is_doi)
        except django.db.utils.IntegrityError as e:
            # UNIQUE constraint failed: ezidapp_shoulder.name, ezidapp_shoulder.type
            raise django.core.management.CommandError(
                "Shoulder, name or type already exists. Error: {}".format(str(e))
            )
        except Exception as e:
            raise django.core.management.CommandError(
                "Unable to create database record for shoulder. Error: {}".format(
                    str(e)
                )
            )

        try:
            self.add_shoulder_file_record(noid_str, prefix_str, name_str)
        except Exception as e:
            raise django.core.management.CommandError(
                "Unable to create shoulder record in master file. Error: {}".format(
                    str(e)
                )
            )

        self.create_minter_database(naan_str, shoulder_str)

        print("Shoulder created successfully. Restart the EZID service to activate.")

    def assert_valid_name(self, name_str):
        name_set = [x.name for x in ezidapp.models.Shoulder.objects.all()]

        if name_str not in name_set:
            print("Name must be one of:")
            for s in sorted(name_set):
                print(u"  {}".format(s))
            raise django.core.management.base.CommandError(
                "Invalid name: {}".format(name_str)
            )

    def add_shoulder_db_record(self, noid_str, prefix_str, name_str, is_doi):
        """Add a new shoulder row to the shoulder table"""
        ezidapp.models.Shoulder.objects.create(
            prefix=prefix_str,
            type="DOI" if is_doi else "ARK",
            name=name_str,
            minter="ezid:/{}".format(noid_str),
            datacenter=None,
            crossrefEnabled=False,
            isTest=False,
        )

    def add_shoulder_file_record(self, noid_str, prefix_str, name_str):
        """Add a new shoulder entry to the master shoulders file"""
        _url = config.get("shoulders.url")

        assert _url.startswith(FILE_PROTOCOL)

        file_path = _url[len(FILE_PROTOCOL) :]
        now = datetime.datetime.now()

        with open(file_path, "a") as f:
            f.write(":: {}\n".format(prefix_str))
            f.write("type: shoulder\n")
            f.write("manager: ezid\n")
            f.write("name: {}\n".format(name_str))
            f.write("date: {:04d}.{:02d}.{:02d}\n".format(now.year, now.month, now.day))
            f.write("minter: ezid:/{}\n".format(noid_str))
            f.write("\n")

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
