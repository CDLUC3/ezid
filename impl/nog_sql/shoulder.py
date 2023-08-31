#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import datetime
import logging

import django.contrib.auth.models
import django.core
import django.core.management
import django.db
import django.db.transaction
import django.db.utils

import ezidapp.models.datacenter
import ezidapp.models.shoulder
import impl.nog.id_ns
import impl.nog_sql.ezid_minter

log = logging.getLogger(__name__)


def assert_valid_datacenter_name(name_str):
    name_set = {x.name for x in ezidapp.models.shoulder.Shoulder.objects.all()}
    if name_str not in name_set:
        log.error(
            'Datacenter must be one of:\n{}'.format(
                '\n'.join('  {}'.format(x) for x in sorted(name_set))
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
        shoulder_model = ezidapp.models.shoulder.Shoulder.objects.filter(
            type=type_str.upper(), name=org_str
        ).get()
    except ezidapp.models.shoulder.Shoulder.DoesNotExist:
        pass
    else:
        raise django.core.management.CommandError(
            'Organization "{}" already has a {} shoulder: {}'.format(
                org_str, type_str.upper(), shoulder_model.prefix
            )
        )


def assert_super_shoulder_slash(ns, is_super_shoulder, is_force):
    """Assert that super-shoulder ends with "/" or that --skip-checks was set."""
    if not is_super_shoulder:
        return
    if not str(ns).endswith('/'):
        if is_force:
            log.info('Accepting super-shoulder not ending with "/" due to --skip-checks')
        else:
            raise django.core.management.CommandError(
                'Super-shoulder normally ends with "/". Use --skip-checks to skip this check '
                'and create a super-shoulder not ending with "/"'
            )


def assert_valid_datacenter(datacenter_str):
    datacenter_set = {x.symbol for x in ezidapp.models.datacenter.Datacenter.objects.all()}
    if datacenter_str not in datacenter_set:
        log.error(
            'Datacenter must be one of:\n{}'.format(
                '\n'.join('  {}'.format(x) for x in sorted(datacenter_set))
            )
        )
        raise django.core.management.CommandError('Invalid datacenter: {}'.format(datacenter_str))


def dump_shoulders():
    log.info('Shoulders:')
    for m in ezidapp.models.shoulder.Shoulder.objects.all().order_by('name', 'prefix'):
        log.info(f'{m.prefix:<20} {m.name}')


def dump_datacenters():
    # for x in ezidapp.models.datacenter.Datacenter.objects.all():
    #     log.info(x)
    for x in ezidapp.models.datacenter.Datacenter.objects.all():
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
    assert isinstance(ns, impl.nog.id_ns.IdNamespace)
    assert_shoulder_type_available(organization_name_str, ns.scheme)
    assert_super_shoulder_slash(ns, is_super_shoulder, is_force)
    log.info('Creating minter for {} shoulder: {}'.format(ns.scheme.upper(), ns))
    # Add new minter to the minter table  with intial state.
    try:
        prefix = impl.nog_sql.ezid_minter.create_minter_database(ns)
        log.debug(f'Minter created for prefix: {prefix}')
    except Exception as e:
        if is_debug:
            raise
        raise django.core.management.CommandError(
            'Unable to create database record for minter. Error: {}'.format(str(e))
        )
    
    # Add new shoulder row to the shoulder table.
    try:
        minterVal = "ezid-minter"
        if is_super_shoulder:
            minterVal = ''

        # get the corresponding agency
        # choice of 3
        # select * from ezidapp_registrationAgency;
        agency_code = "ezid"
        if ns.scheme.upper() == "DOI":
            agency_code = "datacite"
            if is_crossref:
                agency_code = "crossref"
        agency = ezidapp.models.shoulder.RegistrationAgency.objects.get(
            registration_agency=agency_code
        )
        print(agency)
        # Only one type of shoulder, "shoulder"
        # see: select * from ezidapp_shouldertype;
        shoulder_type = ezidapp.models.shoulder.ShoulderType.objects.get(shoulder_type="shoulder")
        print(shoulder_type)

        ezidapp.models.shoulder.Shoulder.objects.create(
            prefix=ns,
            type=ns.scheme.upper(),
            name=organization_name_str,
            minter=minterVal,
            datacenter=datacenter_model,
            crossrefEnabled=is_crossref,
            isTest=is_test,
            isSupershoulder=is_super_shoulder,
            manager='ezid',
            prefix_shares_datacenter=is_sharing_datacenter,
            date=datetime.date.today(),
            active=True,
            registration_agency=agency,
            shoulder_type=shoulder_type,
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
