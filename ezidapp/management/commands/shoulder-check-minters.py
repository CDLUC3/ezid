#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Check outdated minters - Next identifier to be minted is already in the database 
"""

import argparse
import logging
import pathlib

import django.contrib.auth.models
import django.core.management
import django.db.transaction
from django.core.exceptions import ObjectDoesNotExist

import ezidapp.models.identifier
import ezidapp.models.shoulder
import impl.nog_sql.exc
import impl.nog_sql.ezid_minter
import impl.nog_sql.util

log = logging.getLogger(__name__)


class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.opt = None

    def add_arguments(self, parser):
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Debug level logging',
        )

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog_sql.util.log_setup(__name__, opt.debug)

        log.info('Check outdated minters ...')

        try:
            return self.check_all_minters()
        except Exception as e:
            if opt.debug:
                raise
            raise django.core.management.CommandError(
                'Unable to check all minters. Error: {}'.format(str(e))
            )

    def check_all_minters(self):
        error_dict = {}
        total_count = 0

        def count_error(s):
            error_dict.setdefault(s, 0)
            error_dict[s] += 1

        for shoulder_model in ezidapp.models.shoulder.Shoulder.objects.all().order_by('prefix'):
            total_count += 1

            try:
                ok_str = self.check_minter(shoulder_model)
            except CheckError as e:
                tags_str = ', '.join(
                    [
                        '{}={}'.format(k, 'yes' if v is True else 'no' if v is False else v)
                        for k, v in (
                            ('active', shoulder_model.active),
                            ('supershoulder', shoulder_model.isSupershoulder),
                            ('test', shoulder_model.isTest),
                        )
                    ]
                )
                log.error(
                    '{:<20} Check failed: {}{}{}'.format(
                        shoulder_model.prefix,
                        e.key,
                        ': {}'.format(str(e)) if str(e) else '',
                        ' ({})'.format(tags_str),
                    )
                )
                count_error('{} ({})'.format(e.key, tags_str))
            except Exception as e:
                log.error(
                    'Exception while checking shoulder "{}": {}'.format(
                        shoulder_model.prefix, repr(e)
                    )
                )
                count_error('Unhandled exception')
            else:
                log.info('{:<20} {}'.format(shoulder_model.prefix, ok_str))

        log.info('-' * 50)
        log.info('Check completed')
        log.info('Total shoulders checked: {}'.format(total_count))

        if not error_dict:
            log.info('All checks passed!')
            return

        log.error('Errors:')
        for k, v in list(error_dict.items()):
            log.error('{:>4} shoulders have error: {}'.format(v, k))

    def check_minter(self, shoulder_model):
        try:
            minter = ezidapp.models.minter.Minter.objects.get(prefix=shoulder_model.prefix)
            if shoulder_model.prefix != minter.prefix:
                raise CheckError(
                    'Shoulder prefix does not match minter prefix', 
                    f'shoulder.prefix: {shoulder_model.prefix}, minter.prefix: {minter.prefix}')
        except ObjectDoesNotExist:
            raise CheckError('No minter registered', f'No minter is registered for prefix: {shoulder_model.prefix}')
        except Exception as ex:
            raise CheckError('Get minter failed', f'Get minter by prefix {shoulder_model.prefix} failed with error: {ex}')

        try:
            minted_id = impl.nog_sql.ezid_minter.mint_id(shoulder_model, dry_run=True)
        except impl.nog_sql.exc.MinterError as e:
            raise CheckError('Minting test identifier failed', 'Error: {}'.format(str(e)))

        if shoulder_model.prefix.startswith('doi:'):
            id_ns = shoulder_model.prefix + minted_id.upper()
        elif shoulder_model.prefix.startswith('ark:/'):
            id_ns = shoulder_model.prefix + minted_id.lower()
        else:
            raise CheckError(
                'Prefix must start with "doi:" or "ark:/"',
                'Bad prefix: "{}"'.format(shoulder_model.prefix),
            )

        is_in_store = ezidapp.models.identifier.Identifier.objects.filter(identifier=id_ns).exists()
        is_in_search = ezidapp.models.identifier.SearchIdentifier.objects.filter(
            identifier=id_ns
        ).exists()
        if is_in_store or is_in_search:
            raise CheckError(
                'Next identifier to be minted is already in the database (outdated minter)',
                'Existing identifier: "{}" "{}"'.format(
                    id_ns,
                    ' and '.join(
                        [
                            ('is in {}' if f else 'is not in {}').format(n)
                            for n, f in zip(('Store', 'Search'), (is_in_store, is_in_search))
                        ]
                    ),
                ),
            )

        return 'OK: Preview of next ID: {}'.format(id_ns)


class CheckError(Exception):
    def __init__(self, key, msg=None):
        self.key = key
        super(CheckError, self).__init__(msg)
