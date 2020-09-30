from __future__ import absolute_import, division, print_function

import datetime
import logging

import django.core
import django.core.management
import django.db

import ezidapp.models
import nog.id_ns

try:
    import bsddb
except ImportError:
    import bsddb3 as bsddb

import django.contrib.auth.models
import django.core.management
import django.db.transaction

import nog.minter


log = logging.getLogger(__name__)


def assert_valid_datacenter_name(name_str):
    name_set = {x.name for x in ezidapp.models.Shoulder.objects.all()}
    if name_str not in name_set:
        log.error(
            'Datacenter must be one of:\n{}'.format(
                '\n'.join(u'  {}'.format(x) for x in sorted(name_set))
            )
        )
        raise django.core.management.CommandError('Invalid name: {}'.format(name_str))


def assert_shoulder_type_available(org_str, type_str):
    """Assert that shoulder of {type_str} does not already exist for {org_str}

    Args:
        org_str (str): Name of organization
        type_str (str): Shoulder type to check for. Must be 'doi' or 'ark'
    """
    assert type_str in ('doi', 'ark'), 'Invalid shoulder type: {}'.format(type_str)
    try:
        shoulder_model = ezidapp.models.Shoulder.objects.filter(
            type=type_str.upper(), name=org_str
        ).get()
    except ezidapp.models.Shoulder.DoesNotExist:
        pass
    else:
        raise django.core.management.CommandError(
            'Organization "{}" already has a {} shoulder: {}'.format(
                org_str, type_str.upper(), shoulder_model.prefix
            )
        )


def assert_super_shoulder_slash(ns, is_super_shoulder, is_force):
    """Assert that super-shoulder ends with "/" or that --force was set"""
    if not is_super_shoulder:
        return
    if str(ns).endswith('/'):
        if is_force:
            log.info('Accepting super-shoulder not ending with "/" due to --force')
        else:
            raise django.core.management.CommandError(
                'Super-shoulder normally ends with "/". Use --force to skip this check '
                'and create a super-shoulder not ending with "/"'
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
    for m in ezidapp.models.Shoulder.objects.all().order_by('name', 'prefix'):
        log.info('{:<20} {} '.format(m.prefix.encode('utf-8'), m.name.encode('utf-8')))


def dump_datacenters():
    # for x in ezidapp.models.SearchDatacenter.objects.all():
    #     log.info(x)
    for x in ezidapp.models.StoreDatacenter.objects.all():
        log.info(x)


def create_shoulder(
    ns,
    organization_name_str,
    datacenter_model,
    is_crossref,
    is_test,
    is_super_shoulder,
    is_sharing_datacenter,
    is_force,
    is_debug,
):
    assert isinstance(ns, nog.id_ns.IdNamespace)
    assert_shoulder_type_available(organization_name_str, ns.scheme)
    assert_super_shoulder_slash(ns, is_super_shoulder, is_force)
    log.info('Creating minter for {} shoulder: {}'.format(ns.scheme.upper(), ns))
    # Create the minter BerkeleyDB.
    bdb_path = nog.minter.create_minter_database(ns)
    log.debug('Minter BerkeleyDB created at: {}'.format(bdb_path.as_posix()))
    # Add new shoulder row to the shoulder table.
    try:
        ezidapp.models.Shoulder.objects.create(
            prefix=ns,
            type=ns.scheme.upper(),
            name=organization_name_str,
            minter="ezid:/{}".format('/'.join(bdb_path.parts[-3:-1]),),
            datacenter=datacenter_model,
            crossrefEnabled=is_crossref,
            isTest=is_test,
            isSupershoulder=is_super_shoulder,
            manager='ezid',
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
