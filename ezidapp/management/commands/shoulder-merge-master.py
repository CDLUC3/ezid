"""Permanently merge the master_shoulders.txt file into the database.
"""

from __future__ import absolute_import, division, print_function

import argparse
import datetime
import logging

import django.contrib.auth.models
import django.core.management
import django.core.management.base
import django.db.transaction

import ezidapp.management.commands.resources.reload as reload
import ezidapp.models
import ezidapp.models.store_datacenter
import shoulder_parser
import utils.filesystem

MASTER_SHOULDERS_PATH = utils.filesystem.abs_path('../../../master_shoulders.txt')
DEBUG = True


class Command(django.core.management.base.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.opt = None

    def add_arguments(self, parser):
        parser.add_argument(
            '--debug', action='store_true', help='Debug level logging',
        )

    def handle(self, *_, **opt):
        opt = argparse.Namespace(**opt)

        if opt.debug:
            logging.getLogger('').setLevel(logging.DEBUG)

        try:
            with django.db.transaction.atomic():
                self.add_shoulder_db_records()
        except Exception as e:
            if DEBUG:
                raise
            raise django.core.management.CommandError(
                'Merge failed. Error: {}'.format(str(e))
            )
        else:
            print('Completed successfully')

    def add_shoulder_db_records(self):
        with open(MASTER_SHOULDERS_PATH, 'r') as f:
            entries, errors, warnings = shoulder_parser.parse(f.read())

        if errors:
            print('File validation error(s):')
            for e in errors:
                print("  (line %d) %s" % e)

        if warnings:
            print('File validation warnings(s):')
            for e in warnings:
                print("  (line %d) %s" % e)

        # list of dicts to dict keyed on 'key'
        file_dict = {v['key']: v for v in entries}

        # Delete db shoulders not in file

        delete_list = []

        for s in ezidapp.models.Shoulder.objects.all():
            if s.prefix not in file_dict:
                delete_list.append(s.prefix)

        if delete_list:
            print('Deleting db records for shoulders not in file:')
            print(','.join(delete_list))

        # ezidapp.models.Shoulder.objects.filter(prefix__in=delete_list).delete()

        # Create and update db entries to match file

        # file entry:
        # {
        #     'name': 'UCSD eScholarship',
        #     'registration_agency': 'crossref',
        #     'active': True,
        #     'manager': 'ezid',
        #     'minter': 'https://n2t.net/a/ezid/m/ark/b5070/sd2',
        #     'key': 'doi:10.5070/SD2',
        #     'date': '2020.03.03',
        #     'type': 'shoulder',
        # }

        for k, v in file_dict.items():

            if v['type'] != 'shoulder':
                continue

            ezidapp.models.Shoulder.objects.update_or_create(
                defaults=dict(
                    name=v['name'],
                    registration_agency=(
                        ezidapp.models.RegistrationAgency.objects.get_or_create(
                            registration_agency='ezid'
                        )[0]
                    ),
                    active=v['active'],
                    manager=v['manager'],
                    minter=v.get('minter', 'ezid:'),
                    date=datetime.datetime.strptime(
                        v.get('date', '1970.01.01'), '%Y.%m.%d'
                    ),
                    shoulder_type=(
                        ezidapp.models.ShoulderType.objects.get_or_create(
                            shoulder_type=v['type']
                        )[0]
                    ),
                    isTest=False,
                ),
                prefix=k,
            )

        # As suggested in a comment by Greg, we replace the hardcoded "isDoi" and
        # "crossrefEnabled" based logic for registration_entry with a text field.
        for s in ezidapp.models.Shoulder.objects.all():
            if s.isDoi:
                if s.registration_agency == 'crossref' or s.crossrefEnabled:
                    s.crossrefEnabled = True
                    reg_agency_str = 'crossref'
                else:
                    s.crossrefEnabled = False
                    reg_agency_str = 'datacite'
            else:
                s.crossrefEnabled = False
                reg_agency_str = 'ezid'
            s.registration_agency = ezidapp.models.RegistrationAgency.objects.get_or_create(
                registration_agency=reg_agency_str
            )[
                0
            ]
            s.save()

        # Validate and add DOI/ARK type strings
        for s in ezidapp.models.Shoulder.objects.all():
            # - Validate existing DOI/ARK types
            assert s.type in (s.prefix[:3].upper(), '')
            # - Fill in missing types
            s.type = s.prefix[:3].upper()
            s.save()

        print('{} merged'.format(MASTER_SHOULDERS_PATH))

        reload.trigger_reload()