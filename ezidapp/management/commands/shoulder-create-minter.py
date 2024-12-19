#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Create a minter for an existing shoulder
"""

import argparse
import logging

import django.contrib.auth.models
import django.core.management
import django.db.transaction

import ezidapp.models.shoulder
import impl.nog_sql.util
import impl.nog_sql.ezid_minter

log = logging.getLogger(__name__)


class Command(django.core.management.BaseCommand):
    help = __doc__

    def __init__(self):
        super(Command, self).__init__()
        self.opt = None

    def add_arguments(self, parser):
        parser.add_argument(
            'shoulder_str',
            metavar='shoulder',
            help="Full shoulder. E.g., ark:/99999/fk4",
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Debug level logging',
        )

    def handle(self, *_, **opt):
        self.opt = opt = argparse.Namespace(**opt)
        impl.nog_sql.util.log_setup(__name__, opt.debug)

        shoulder_str = opt.shoulder_str
    
        log.info(f"Getting shoulder {shoulder_str}")
        try:
            shoulder_model = ezidapp.models.shoulder.Shoulder.objects.get(prefix=shoulder_str)
        except ezidapp.models.shoulder.Shoulder.DoesNotExist:
            log.error("Shoulder string %s not found in Shoulder model", shoulder_str)
            raise django.core.management.CommandError('Invalid shoulder: {}'.format(shoulder_str))
        
        if shoulder_model.minter.strip() != '':
            raise django.core.management.CommandError(
                f'Shoulder {shoulder_str} already has a minter: {shoulder_model.minter}'
            )
       
        minter_exists = ezidapp.models.minter.Minter.objects.filter(prefix=shoulder_str).exists()
        if minter_exists:
            log.error(f"Shoulder/Prefix {shoulder_str} found in Minter model")
            raise django.core.management.CommandError(f'Minter exists for {shoulder_str}. No need to recreate.')
       
        try:
            ns = impl.nog_sql.id_ns.IdNamespace.split_ark_namespace(shoulder_str)
        except impl.nog_sql.id_ns.IdentifierError as e:
            raise django.core.management.CommandError(str(e))
        
        try:
            with django.db.transaction.atomic():
                shoulder_model.minter = shoulder_str
                shoulder_model.save()
                impl.nog_sql.ezid_minter.create_minter_database(ns)
                log.info(f'A minter was created for Shoulder/Prefix: {shoulder_str}')
        except Exception as ex:
            log.error(f'Create a minter for shoulder/prefix {shoulder_str} failed')
            
