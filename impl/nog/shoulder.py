from __future__ import absolute_import, division, print_function

import datetime
import logging

import django.core
import django.core.management
import django.db

import ezidapp.models

try:
    import bsddb
except ImportError:
    import bsddb3 as bsddb

import django.contrib.auth.models
import django.core.management
import django.db.transaction

log = logging.getLogger(__name__)


def assert_valid_datacenter_name(name_str):
    name_set = {x.name for x in ezidapp.models.Shoulder.objects.all()}
    if name_str not in name_set:
        log.error(
            'Datacenter must be one of:\n{}'.format(
                '\n'.join(u'  {}'.format(x) for x in sorted(name_set))
            )
        )
        raise django.core.management.CommandError(
            'Invalid name: {}'.format(name_str)
        )


def assert_valid_datacenter(datacenter_str):
    datacenter_set = {x.symbol for x in ezidapp.models.StoreDatacenter.objects.all()}
    if datacenter_str not in datacenter_set:
        log.error(
            'Datacenter must be one of:\n{}'.format(
                '\n'.join(u'  {}'.format(x) for x in sorted(datacenter_set))
            )
        )
        raise django.core.management.CommandError(
            'Invalid datacenter: {}'.format(datacenter_str)
        )


def dump_shoulders():
    log.info('Shoulders:')
    for x in ezidapp.models.Shoulder.objects.all().order_by('name', 'prefix'):
        log.info(x)


def dump_datacenters():
    # for x in ezidapp.models.SearchDatacenter.objects.all():
    #     log.info(x)
    for x in ezidapp.models.StoreDatacenter.objects.all():
        log.info(x)


def create_shoulder_db_record(
    namespace_str,
    type_str,
    name_str,
    bdb_path,
    datacenter_model,
    is_crossref,
    is_test,
    is_super_shoulder,
    is_sharing_datacenter,
    is_debug,
):
    """Add a new shoulder row to the shoulder table"""
    try:
        ezidapp.models.Shoulder.objects.create(
            prefix=namespace_str,
            type=type_str.upper(),
            name=name_str,
            minter="ezid:/{}".format('/'.join(bdb_path.parts[-3:-1]),),
            datacenter=datacenter_model,
            crossrefEnabled=is_crossref,
            isTest=is_test,
            isSupershoulder=is_super_shoulder,
            prefix_shares_datacenter=is_sharing_datacenter,
            date=datetime.date.today(),
            active=True,
        )
    except django.db.utils.IntegrityError as e:
        raise django.core.management.CommandError(
            'Shoulder, name or type already exists. Error: {}'.format(str(e))
        )
    except Exception as e:
        if is_debug:
            raise
        raise django.core.management.CommandError(
            'Unable to create database record for shoulder. Error: {}'.format(str(e))
        )
