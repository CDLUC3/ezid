#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Create BerkeleyDB minter instances for any shoulders in the database that
are referencing non-existing minters.
"""

import os
import argparse
import logging
import socket

import django.conf
import django.contrib.auth.models
import django.core.management
import django.db.transaction
from django.db.models import Q

import ezidapp.models.shoulder
import ezidapp.models.datacenter
import ezidapp.models.identifier
import ezidapp.models.async_queue
import impl.nog_sql.ezid_minter
import impl.nog_sql.util
import impl.client_util

log = logging.getLogger(__name__)

base_url = django.conf.settings.EZID_BASE_URL
admin_username = django.conf.settings.ADMIN_USERNAME
admin_password = django.conf.settings.ADMIN_PASSWORD
username = 'apitest'
password = 'apitest'

test_new_prefixes = {
    'ark': 'ark:/99999/fk88',
    'datacite': 'doi:10.5072/FK7',
    'crossref': 'doi:10.31223/FK3'
}

record_datacite = {
    '_profile': 'datacite',
    '_target': "https://google.com",
    'datacite.publicationyear': '2023',
    'datacite.type': 'Dataset',
    'datacite.title': 'datacite test record',
    'datacite.publisher': 'test publisher', 
    'datacite.creator': 'unknown',
}

xml_record = (
    '<?xml version="1.0"?>'
    '<journal xmlns="http://www.crossref.org/schema/5.3.0" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
    'xmlns:jats="http://www.ncbi.nlm.nih.gov/JATS1" '
    'xsi:schemaLocation="http://www.crossref.org/schema/5.3.0 '
    'http://www.crossref.org/schema/deposit/crossref5.3.0.xsd" type="preprint">'
    '<journal_metadata language="en">'
    '<full_title>Journal of Awesome Cat Names</full_title><abbrev_title>JACN</abbrev_title>'
    '<!-- placeholder DOI, will be overwritten when DOI is minted -->  <doi_data>    <doi></doi>'
    '<resource>https://dev.eartharxiv.org/repository/view/1777/</resource></doi_data>'
    '</journal_metadata></journal>'
    )
record_crossref = {
    '_crossref': 'yes',
    '_profile': 'crossref',
    '_target': "https://google.com",
    'crossref': xml_record,
}

queueType = {
    'crossref': ezidapp.models.async_queue.CrossrefQueue,
    'datacite': ezidapp.models.async_queue.DataciteQueue,
    'search': ezidapp.models.async_queue.SearchIndexerQueue
}

testsets = {
    '1': 'mint, create, update and delete IDs on exisiting shoulders',
    '2': 'create new shoulders and mint, create, update and delete IDs on newly created shoulders',
    '3': 'combine test 1 and 2'
}

if 'HOSTNAME' in os.environ:
    HOSTNAME = os.environ['HOSTNAME']
else:
    HOSTNAME = socket.gethostname()

class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.opt = None

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-level',
            type=int, 
            choices=range(1, 4),
            required=True,
            help=f"Setup test level; 1={testsets.get('1')}, 2={testsets.get('2')}, 3={testsets.get('3')}",
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Debug level logging',
        )

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog_sql.util.log_setup(__name__, opt.debug)

        test_level  = str(opt.test_level)
        if test_level == '3':
            testset = f"combine test 1 & 2: \ntest1: {testsets.get('1')}\ntest2: {testsets.get('2')}"
        else:
            testset = testsets.get(test_level)

        log.info('Testing EZID ...')
        log.info(f"Running testset {test_level}: {testset}")
        
        print(f'You are running this command on host: {HOSTNAME}')
        on_prd  = input('Do you want to proceed? Yes/No\n')
        if on_prd.upper() != 'YES':
            print('Abort!')
            exit()

        if test_level in ['1', '3']:
            self.test_existing_shoulder()
       
        if test_level in ['2', '3']:
            self.test_regular_shoulder(opt)
            self.test_super_shoulder(opt)

    def test_data_prep(self):
        try:
            for key, prefix in test_new_prefixes.items():
                self.delete_shoulder_minter(prefix)
        except Exception as ex:
            raise django.core.management.CommandError(f'Deleting exisiting shoulder/minter failed: {ex}')

    def test_data_cleanup(self):
        try:
            for key, prefix in test_new_prefixes.items():
                self.delete_shoulder_minter(prefix)
        except Exception as ex:
            raise django.core.management.CommandError(f'Deleting exisiting shoulder/minter failed: {ex}')

    def test_existing_shoulder(self):
        prefix = django.conf.settings.SHOULDERS_ARK_TEST
        if prefix:
            self.mint_update_delete_identifier(prefix, record_datacite)
            self.create_update_delete_identifier(prefix, record_datacite)

        prefix = django.conf.settings.SHOULDERS_DOI_TEST
        if prefix:
            self.mint_update_delete_identifier(prefix, record_datacite)
            self.create_update_delete_identifier(prefix, record_datacite)

        prefix = django.conf.settings.SHOULDERS_CROSSREF_TEST
        if prefix:
            self.mint_update_delete_identifier(prefix, record_crossref, is_crossref=True)
            self.create_update_delete_identifier(prefix, record_crossref, is_crossref=True)

    def test_regular_shoulder(self, opt):
        try:
            self.test_data_prep()

            log.info('==== Creating ARK, Datacite DOI and Crossref DOI shoulders ...')

            success_flag = True
            prefix = test_new_prefixes.get('ark')
            org_name = f'{prefix} test'
            shoulder, minter = self.check_create_sholuder_and_minter('ark', prefix, org_name)
            
            # reenable log handler as sub-command removes existing handlers
            impl.nog_sql.util.log_setup(__name__, opt.debug)

            if not (shoulder.prefix == prefix and shoulder.isArk == True
                    and shoulder.isDatacite == False
                    and shoulder.isCrossref == False
                    and shoulder.isSupershoulder == False
                    ):
                success_flag = False
                log.error(f'#### FAILED create ARK shoulder: {prefix}, org_name: {org_name}')
                
            if (minter.prefix != prefix ):
                success_flag = False
                log.error(f'#### FAILED create minter for prefix: {prefix}')

            if success_flag:
                log.info(f'#### OK create AKR shoulder: {prefix}, org_name: {org_name}')

            success_flag = True
            prefix = test_new_prefixes.get('datacite')
            org_name = f'{prefix} test'
            datacenter_symbol = 'CDL.CDL'
            shoulder, minter = self.check_create_sholuder_and_minter('doi', prefix, org_name, datacenter_symbol)
            
            impl.nog_sql.util.log_setup(__name__, opt.debug)

            if not (shoulder.prefix == prefix and shoulder.isDoi == True
                    and shoulder.isDatacite == True 
                    and shoulder.isCrossref == False
                    and shoulder.datacenter.symbol == datacenter_symbol
                    and shoulder.isSupershoulder == False):
                success_flag = False
                log.error(f'FAILED create Datacite DOI shoulder : {prefix}, org_name: {org_name}')
            
            if (minter.prefix != prefix ):
                success_flag = False
                log.error(f'FAILED create minter for prefix: {prefix}')

            if success_flag:
                log.info(f'#### OK create Datacite DOI shoulder: {prefix}, org_name: {org_name}')

            success_flag = True
            prefix = test_new_prefixes.get('crossref')
            org_name = f'{prefix} test'
            shoulder, minter = self.check_create_sholuder_and_minter('doi', prefix, org_name, is_crossref=True)

            impl.nog_sql.util.log_setup(__name__, opt.debug)

            if not (shoulder.prefix == prefix and shoulder.isDoi == True
                    and shoulder.isDatacite == False
                    and shoulder.isCrossref == True
                    and shoulder.datacenter is None
                    and shoulder.isSupershoulder == False):
                success_flag = False
                log.error(f'FAILED create Crossref DOI shoulder : {prefix}, org_name: {org_name}')
            
            if (minter.prefix != prefix ):
                success_flag = False
                log.error(f'FAILED create minter for prefix: {prefix}')

            if success_flag:
                log.info(f'#### OK create Crossref DOI shoulder: {prefix}, org_name: {org_name}')

        except Exception as e:
            raise django.core.management.CommandError(
                f'Unable to create shoulder/minter for prefix {prefix}. Error: {e}'
            )

        shoulder_type = 'ark'
        prefix = test_new_prefixes.get(shoulder_type)
        self.test_minter_and_minting_functions(opt, prefix, shoulder_type)

        prefix = test_new_prefixes.get('datacite')
        log.info(f'==== Minting 2 identifiers on minter with prefix: {prefix}')
        self.test_shoulder_mint_cmd(prefix)

        impl.nog_sql.util.log_setup(__name__, opt.debug)
        log.info(f'==== Updating organization name for shoulder: {prefix}')
        self.test_shoulder_update_organization(prefix, f'{prefix} new org_name')

        impl.nog_sql.util.log_setup(__name__, opt.debug)
        log.info(f'==== Updating datacenter for shoulder: {prefix}')
        self.test_shoulder_update_datacenter(prefix, 'CDL.UCD')
       
        impl.nog_sql.util.log_setup(__name__, opt.debug)
        log.info('==== Mint, create, update, delete identifiers via EZID APIs')
        self.mint_update_delete_identifier(prefix, record_datacite)
        self.create_update_delete_identifier(prefix, record_datacite)

        prefix = test_new_prefixes.get('crossref')
        log.info(f'==== Minting 2 identifiers on minter with prefix: {prefix}')
        self.test_shoulder_mint_cmd(prefix)

        impl.nog_sql.util.log_setup(__name__, opt.debug)
        log.info(f'==== Updating organization name for shoulder: {prefix}')
        self.test_shoulder_update_organization(prefix, f'{prefix} new org_name')
        try:
            self.test_shoulder_update_datacenter(prefix, 'CDL.UCD')
        except Exception as ex:
            assert 'Unable to set datacenter. Shoulder is registered with Crossref' in f'{ex}'

        impl.nog_sql.util.log_setup(__name__, opt.debug)
        log.info('==== Mint, create, update, delete identifiers via EZID APIs')
        self.mint_update_delete_identifier(prefix, record_crossref, is_crossref=True)
        self.create_update_delete_identifier(prefix, record_crossref, is_crossref=True)

        self.test_data_cleanup()

    def test_minter_and_minting_functions(self, opt, prefix, shoulder_type):
        log.info(f'==== Minting 2 identifiers on minter with prefix: {prefix}')
        self.test_shoulder_mint_cmd(prefix)

        impl.nog_sql.util.log_setup(__name__, opt.debug)
        log.info(f'==== Updating organization for shoulder: {prefix}')
        self.test_shoulder_update_organization(prefix, f'{prefix} new org_name')
        try:
            self.test_shoulder_update_datacenter(prefix, 'CDL.UCD')
        except Exception as ex:
            if shoulder_type  == 'ark':
                assert f'{ex}' == 'Scheme must be "doi": ark'

        impl.nog_sql.util.log_setup(__name__, opt.debug)
        log.info('==== Mint, create, update, delete identifiers via EZID APIs')
        self.mint_update_delete_identifier(prefix, record_datacite)
        self.create_update_delete_identifier(prefix, record_datacite)

    def test_super_shoulder(self, opt):
        try:
            self.test_data_prep()

            prefix = test_new_prefixes.get('ark')
            org_name = f'{prefix} test'
            log.info(f'Creating AKR shoulder: {prefix}, org_name: {org_name}')
            shoulder, minter = self.check_create_sholuder_and_minter('ark', prefix, org_name, is_super_shoulder=True)
            
            # reenable log handler as sub-command removes existing handlers
            impl.nog_sql.util.log_setup(__name__, opt.debug)

            if not (shoulder.prefix == prefix and shoulder.isArk == True
                    and shoulder.isDatacite == False
                    and shoulder.isCrossref == False
                    and shoulder.isSupershoulder == True
                    ):
                log.error(f'Creating ARK super shoulder: {prefix}, org_name: {org_name}: FAILED')
                
            if minter is not None:
                log.error(f'Super shoulder should not have a minter. Check shoulder and minter for prefix: {prefix}')

            prefix = test_new_prefixes.get('datacite')
            org_name = f'{prefix} test'
            datacenter_symbol = 'CDL.CDL'
            log.info(f'Creating Datacite DOI shoulder: {prefix}, org_name: {org_name}')
            shoulder, minter = self.check_create_sholuder_and_minter('doi', prefix, org_name, datacenter_symbol, is_super_shoulder=True)
            
            impl.nog_sql.util.log_setup(__name__, opt.debug)

            if not (shoulder.prefix == prefix and shoulder.isDoi == True
                    and shoulder.isDatacite == True 
                    and shoulder.isCrossref == False
                    and shoulder.datacenter.symbol == datacenter_symbol
                    and shoulder.isSupershoulder == True):
                log.error(f'Creating Datacite DOI super shoulder : {prefix}, org_name: {org_name}: FAILED')
            
            if minter is not None:
                log.error(f'Super shoulder should not have a minter. Check shoulder and minter for prefix: {prefix}')

            prefix = test_new_prefixes.get('crossref')
            org_name = f'{prefix} test'
            log.info(f'Creating Crossref DOI shoulder: {prefix}, org_name: {org_name}')
            shoulder, minter = self.check_create_sholuder_and_minter('doi', prefix, org_name, is_crossref=True, is_super_shoulder=True)

            impl.nog_sql.util.log_setup(__name__, opt.debug)

            if not (shoulder.prefix == prefix and shoulder.isDoi == True
                    and shoulder.isDatacite == False
                    and shoulder.isCrossref == True
                    and shoulder.datacenter is None
                    and shoulder.isSupershoulder == True):
                log.error(f'Creating Crossref DOI super shoulder : {prefix}, org_name: {org_name}: FAILED')
            
            if minter is not None:
                log.error(f'Super shoulder should not have a minter. Check shoulder and minter for prefix: {prefix}')

        except Exception as e:
            raise django.core.management.CommandError(
                f'Unable to create shoulder/minter for prefix {prefix}. Error: {e}'
            )

        log.info('#### Create super shoulders completed successfully')

        prefix = test_new_prefixes.get('ark')
        impl.nog_sql.util.log_setup(__name__, opt.debug)
        self.create_update_delete_identifier(prefix, record_datacite)

        prefix = test_new_prefixes.get('datacite')
        impl.nog_sql.util.log_setup(__name__, opt.debug)
        self.create_update_delete_identifier(prefix, record_datacite)

        prefix = test_new_prefixes.get('crossref')
        impl.nog_sql.util.log_setup(__name__, opt.debug)
        self.create_update_delete_identifier(prefix, record_crossref, is_crossref=True)

        self.test_data_cleanup()


    def mint_update_delete_identifier(self, prefix, record, is_crossref=False):
        self.grant_user_access_to_shoulder(username, prefix)
        shoulder, id_created, text = impl.client_util.mint_identifer(base_url, username, password, prefix, record)
        if id_created is not None:
            log.info(f'#### OK mint_id on {shoulder}, ID created: {id_created}')
            
            if is_crossref:
                update_data = {
                    '_status': 'reserved',
                    '_crossref': 'yes',
                }
            else:
                update_data = {
                    '_status': 'reserved',
                }

            # update status from public to reserved
            http_status = impl.client_util.update_identifier(base_url, admin_username, admin_password, id_created, update_data)
            self.log_update_identifier(id_created, update_data, http_status)

            http_status = impl.client_util.delete_identifier(base_url, username, password, id_created)
            self.log_delete_identifier(id_created, http_status)

            self.delete_refidentifier(id_created)

        else:
            log.error(f'#### mint_id on {shoulder} FAILED!')


    def create_update_delete_identifier(self, prefix, record, is_crossref=False):
        self.grant_user_access_to_shoulder(username, prefix)
        identifier = f'{prefix}test_1'
        id_created_1, text_1 = impl.client_util.create_identifer(base_url, username, password, identifier, record)
        id_created_2, text_2 = impl.client_util.create_identifer(base_url, username, password, identifier, record, update_if_exists=True)

        if id_created_1 is None and id_created_2 is None:
            log.error(f'#### create ID {identifier} FAILED!')
        elif id_created_1 and id_created_2 and id_created_1 != id_created_2:
            log.error(f'#### create ID {identifier} FAILED!')
        else:
            if id_created_2.upper() != identifier.upper():
                log.error(f'#### create ID {identifier} FAILED!')
            else:
                log.info(f'#### OK create ID {id_created_2}')
            
            if is_crossref:
                update_data = {
                    '_status': 'reserved',
                    '_crossref': 'yes',
                }
            else:
                update_data = {
                    '_status': 'reserved',
                }

            # update status from public to reserved
            http_status = impl.client_util.update_identifier(base_url, admin_username, admin_password, id_created_2, update_data)
            self.log_update_identifier(id_created_2, update_data, http_status)
            
            http_status = impl.client_util.delete_identifier(base_url, username, password, id_created_2)
            self.log_delete_identifier(id_created_2, http_status)

            self.delete_refidentifier(id_created_2)

    def log_delete_identifier(self, id_created, http_status):
        http_success, status_code, text, err_msg = http_status
        if http_success and status_code == 200:
            log.info(f"#### OK delete identifier - {id_created} ")
        else:
            log.error(f"ERROR delete identifier - delete {id_created} failed - status_code: {status_code}: {text}: {err_msg}")

    def log_update_identifier(self, id_created, update_data, http_status):
        http_success, status_code, text, err_msg = http_status
        if http_success and status_code == 200:
            log.info(f"#### OK update identifier - {id_created} updated with new data: {update_data}")
        else:
            log.error(f"ERROR update identifier - update {id_created} failed - status_code: {status_code}: {text}: {err_msg}")

    def check_create_sholuder_and_minter(self, shoulder_type, prefix, org_name, datacenter_symbol=None, is_crossref=False, is_super_shoulder=False):
        if shoulder_type == 'ark':
            cmd = 'shoulder-create-ark'
            cmd_args = [prefix, org_name]
        elif shoulder_type == 'doi':
            cmd = 'shoulder-create-doi'
            if is_crossref:
                cmd_args = [prefix, org_name, '--crossref']
            elif datacenter_symbol:
                cmd_args = [prefix, org_name, '--datacite', datacenter_symbol]
            else:
                raise django.core.management.CommandError('Datacenter symbol is required for Datacite shoulder')
        else:
            raise django.core.management.CommandError("Shoulder type must be 'ark' or 'doi'")
        if is_super_shoulder:
            cmd_args.append('--super-shoulder')
        
        #log.info(f"Run command '{cmd} {cmd_args}' to create a shoulder and associated minter for prefix: {prefix}")
        try:
            django.core.management.call_command(cmd, *cmd_args)
        except Exception as ex:
             raise django.core.management.CommandError(f"Create shoulder/minter with prefix {prefix} failed: {ex}")
        
        try:
            shoulder = ezidapp.models.shoulder.Shoulder.objects.get(prefix=prefix)
            if is_super_shoulder:
                minter = None
            else:
                minter = ezidapp.models.minter.Minter.objects.get(prefix=prefix)
        except Exception as ex:
             raise django.core.management.CommandError(f"Create shoulder/minter with prefix {prefix} failed: {ex}")
        
        return  shoulder, minter

    def test_shoulder_mint_cmd(self, prefix):
        cmd = 'shoulder-mint'
        cmd_args = [prefix, '--count', '2', '--update']
        django.core.management.call_command(cmd, *cmd_args)

    def test_shoulder_update_datacenter(self, prefix, new_datacenter):
        cmd = 'shoulder-update-datacenter'
        cmd_args = [prefix, new_datacenter]
        django.core.management.call_command(cmd, *cmd_args)

    def test_shoulder_update_organization(self, prefix, new_org_name):
        cmd = 'shoulder-update-organization'
        cmd_args = [prefix, new_org_name]
        django.core.management.call_command(cmd, *cmd_args)

    def delete_shoulder_minter(self, prefix):
        shoulder = ezidapp.models.shoulder.Shoulder.objects.filter(prefix=prefix)
        if shoulder.exists():
            shoulder.delete()

        minter = ezidapp.models.minter.Minter.objects.filter(prefix=prefix)
        if minter.exists():
            minter.delete()

    def delete_refidentifier(self, identifier):
        refIdentifiers = ezidapp.models.identifier.RefIdentifier.objects.filter(identifier=identifier)
        if refIdentifiers.exists():
            for refId in refIdentifiers:
                for key, queue in queueType.items():
                    record_set = queue.objects.filter(Q(refIdentifier_id=refId.pk))
                    if record_set.exists():
                        record_set.delete()
            
            refIdentifiers.delete()
        

    def grant_user_access_to_shoulder(self, username, prefix):
        try:
            user = ezidapp.models.user.User.objects.get(username=username)
            shoulder = ezidapp.models.shoulder.Shoulder.objects.get(prefix=prefix)
            user.shoulders.add(shoulder)
        except Exception as ex:
            raise django.core.management.CommandError(f"Grant access to shoulder {prefix} for user '{username}' failed: {ex}")
