#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Create BerkeleyDB minter instances for any shoulders in the database that
are referencing non-existing minters.
"""

import argparse
import logging

import django.conf
import django.contrib.auth.models
import django.core.management
import django.db.transaction

import ezidapp.models.shoulder
import ezidapp.models.datacenter
import impl.nog_sql.ezid_minter
import impl.nog_sql.util
import impl.client_util

log = logging.getLogger(__name__)

record_1 = {
    '_profile': 'datacite',
    '_target': "https://google.com",
    'datacite.date': '2023',
    'datacite.type': 'Dataset',
    'datacite.title': 'test record on shoulder - ark:/99999/fk88',
    'datacite.publisher': 'test publisher', 
    'datacite.creator': 'unknown',
}

class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.opt = None

    def add_arguments(self, parser):
        # Misc
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Debug level logging',
        )

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog_sql.util.log_setup(__name__, opt.debug)

        base_url = django.conf.settings.EZID_BASE_URL
        admin_username = django.conf.settings.ADMIN_USERNAME
        admin_password = django.conf.settings.ADMIN_PASSWORD

        log.info('Checking EZID on  Dev or Stg ...')
        on_prd  = input('Are you on EZID-Dev or Stg? Yes/No\n')
        if on_prd.upper() != 'YES':
            print('You can only run this command on EZID-Dev or EZID-Stg server. Abort!')
            exit()

        try:
            prefix = 'ark:/99999/fk88'
            org_name = 'ark:/99999/fk88 test'
            log.info(f'Creating AKR shoulder: {prefix}, org_name: {org_name}')
            shoulder, minter = self.check_create_sholuder_and_minter('ark', prefix, org_name)
            
            if not (shoulder.prefix == prefix and shoulder.type == 'ARK' 
                    and shoulder.isSupershoulder == False
                    and shoulder.datacenter == None
                    and shoulder.isCrossref == False):
                log.error(f'Creating ARK shoulder: {prefix}, org_name: {org_name}: FAILED')
                
            if (minter.prefix != prefix ):
                log.error(f'Creating minter for prefix: {prefix}: FAILED')

            # datacite DOI
            prefix = 'doi:10.5072/FK7'
            org_name = 'Datacite doi:10.5072/FK7 test'
            datacenter_symbol = 'CDL.CDL'
            log.info(f'Creating Datacite DOI shoulder: {prefix}, org_name: {org_name}')
            shoulder, minter = self.check_create_sholuder_and_minter('doi', prefix, org_name, datacenter_symbol)

            if not (shoulder.prefix == prefix and shoulder.type == 'DOI' 
                    and shoulder.datacenter.symbol == datacenter_symbol
                    and shoulder.isCrossref == False
                    and shoulder.isSupershoulder == False):
                log.error(f'Creating Datacite DOI shoulder : {prefix}, org_name: {org_name}: FAILED')
            
            if (minter.prefix != prefix ):
                log.error(f'Creating minter for prefix: {prefix}: FAILED')

            # crossref DOI
            prefix = 'doi:10.31223/FK3'
            org_name = 'Crossref doi:10.31223/FK3 test'
            log.info(f'Creating Crossref DOI shoulder: {prefix}, org_name: {org_name}')
            shoulder, minter = self.check_create_sholuder_and_minter('doi', prefix, org_name, is_crossref=True)

            if not (shoulder.prefix == prefix and shoulder.type == 'DOI' 
                    and shoulder.datacenter == None
                    and shoulder.isCrossref == True
                    and shoulder.isSupershoulder == False):
                log.error(f'Creating Crossref DOI shoulder : {prefix}, org_name: {org_name}: FAILED')
            
            if (minter.prefix != prefix ):
                log.error(f'Creating minter for prefix: {prefix}: FAILED')

        except Exception as e:
            if django.conf.settings.DEBUG:
                import logging

                logging.exception('#' * 100)
            if opt.debug:
                raise
            raise django.core.management.CommandError(
                f'Unable to create shoulder/minter for prefix {prefix}. Error: {e}'
            )

        log.info('#### Create shoulder completed successfully')

        username = 'apitest'
        password = 'apitest'
        prefix = 'ark:/99999/fk88'
        self.test_shoulder_mint_cmd(prefix)
        self.grant_user_access_to_shoulder(username, prefix)
        shoulder, id_created, text = impl.client_util.mint_identifers(base_url, username, password, prefix, record_1)
        if id_created is not None:
            log.info(f'#### OK mint_id on {shoulder}, ID created: {id_created}')
            print(f'#### OK mint_id on {shoulder}, ID created: {id_created}')
            update_data = {
                '_status': 'reserved',
            }

            impl.client_util.update_identifier(base_url, admin_username, admin_password, id_created, update_data)

            impl.client_util.delete_identifier(base_url, username, password, id_created)

        else:
            log.error(f'#### ERROR mint_id on {shoulder}')
            print(f'#### ERROR mint_id on {shoulder}')

        


        prefix = 'doi:10.5072/FK7'
        self.test_shoulder_mint_cmd(prefix)
        self.grant_user_access_to_shoulder(username, prefix)

        prefix = 'doi:10.31223/FK3'
        self.test_shoulder_mint_cmd(prefix)
        self.grant_user_access_to_shoulder(username, prefix)




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
            cmd_args.append('--is_super_shoulder')
        
        log.info(f'Delete shoulder/minter with prefix {prefix} if alreay exists')
        try:
            self.delete_shoulder_minter(prefix)
            log.info(f'Shoulder/minter with prefix {prefix} were deleted')
        except Exception as ex:
            raise django.core.management.CommandError(f'Deleting exisiting shoulder/minter failed: {ex}')
        
        log.info(f"Run command '{cmd} {cmd_args}' to create a shoulder and associated minter for prefix: {prefix}")
        try:
            django.core.management.call_command(cmd, *cmd_args)
        except Exception as ex:
             raise django.core.management.CommandError(f"Create shoulder/minter with prefix {prefix} failed: {ex}")
        
        try:
            shoulder = ezidapp.models.shoulder.Shoulder.objects.get(prefix=prefix)
            minter = ezidapp.models.minter.Minter.objects.get(prefix=prefix)
        except Exception as ex:
             raise django.core.management.CommandError(f"Create shoulder/minter with prefix {prefix} failed: {ex}")
        
        return  shoulder, minter

    def test_shoulder_mint_cmd(self, prefix):
        cmd = 'shoulder-mint'
        cmd_args = [prefix, '--count', '2', '--update']
        django.core.management.call_command(cmd, *cmd_args)


    def delete_shoulder_minter(self, prefix):
        shoulder = ezidapp.models.shoulder.Shoulder.objects.filter(prefix=prefix)
        if shoulder.exists():
            shoulder.delete()

        minter = ezidapp.models.minter.Minter.objects.filter(prefix=prefix)
        if minter.exists():
            minter.delete()

    def grant_user_access_to_shoulder(self, username, prefix):
        try:
            user = ezidapp.models.user.User.objects.get(username=username)
            shoulder = ezidapp.models.shoulder.Shoulder.objects.get(prefix=prefix)
            user.shoulders.add(shoulder)
        except Exception as ex:
            raise django.core.management.CommandError(f"Grant access to shoulder {prefix} for user '{username}' failed: {ex}")





        
