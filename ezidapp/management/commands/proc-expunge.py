#! /usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Expunge expired test identifiers

Test identifiers older than Identifiers are discovered by querying the database directly, but expunged by
requesting that the (live) EZID server delete them.
"""

import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.response

import django.conf
import django.conf
import django.db
import django.db.transaction

import ezidapp.management.commands.proc_base
import ezidapp.models.identifier
import ezidapp.models.identifier
import ezidapp.models.news_feed
import ezidapp.models.shoulder
from django.db.models import Q

import impl.enqueue
import impl.ezid

log = logging.getLogger(__name__)


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    name = __name__
    setting = 'DAEMONS_EXPUNGE_ENABLED'

    def __init__(self):
        super().__init__()

    def run(self):
        while not self.terminated():
            max_age_ts = int(
                time.time()) - django.conf.settings.DAEMONS_EXPUNGE_MAX_AGE_SEC
            # TODO: This is a heavy query which can be optimized with better indexes or
            # flags in the DB.
            qs = (
                ezidapp.models.identifier.Identifier.objects.filter(
                    Q(identifier__startswith=django.conf.settings.SHOULDERS_ARK_TEST)
                    | Q(identifier__startswith=django.conf.settings.SHOULDERS_DOI_TEST)
                    | Q(identifier__startswith=django.conf.settings.SHOULDERS_CROSSREF_TEST)
                )
                    .filter(createTime__lte=max_age_ts)
                    .only("identifier")[: django.conf.settings.DAEMONS_MAX_BATCH_SIZE]
            )

            if not qs:
                self.sleep(django.conf.settings.DAEMONS_LONG_SLEEP)
                continue

            for si in qs:
                with django.db.transaction.atomic():
                    impl.enqueue.enqueue(si, "delete", updateExternalServices=True)
                    si.delete()

            self.sleep(django.conf.settings.DAEMONS_BATCH_SLEEP)
