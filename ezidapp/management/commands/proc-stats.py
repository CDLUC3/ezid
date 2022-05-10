#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Identifier statistics

To avoid burdening online identifier processing, statistics are computed periodically by
a daemon thread. We eschew a synchronous, inline approach to maintaining statistics
because identifier changes can be complex (creation times can change, ownership can
change, even users and groups can change) and tracking the effects of those changes on
statistics would require knowledge of an identifier's pre-change state, which is not
recorded.
"""

import datetime
import logging
import pprint
import time

import django.conf
import django.core.management
import django.db
import django.db.models
import django.db.transaction

import ezidapp.management.commands.proc_base
import ezidapp.models.identifier
import ezidapp.models.statistics
import ezidapp.models.user

BATCH_SIZE = 10000

log = logging.getLogger(__name__)


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    name = __name__
    setting = 'DAEMONS_STATISTICS_ENABLED'

    def __init__(self):
        super().__init__()

    def run(self):
        # log.debug(f'In {__name__} run loop...')

        if not self.opt.debug:
            if django.conf.settings.DAEMONS_STATISTICS_COMPUTE_SAME_TIME_OF_DAY:
                self.sleep(self._sameTimeOfDayDelta())
            else:
                # We arbitrarily sleep 10 minutes to avoid putting a burden on the
                # server near startup or reload.
                self.sleep(600)

        while not self.terminated():
            start_ts = self.now()
            self.recomputeStatistics()
            if django.conf.settings.DAEMONS_STATISTICS_COMPUTE_SAME_TIME_OF_DAY:
                self.sleep(self._sameTimeOfDayDelta())
            else:
                self.sleep(
                    max(
                        django.conf.settings.DAEMONS_STATISTICS_COMPUTE_CYCLE
                        - (self.now() - start_ts),
                        0,
                    )
                )

    def recomputeStatistics(self):
        """Recompute and stores identifier statistics

        The old statistics are completely replaced.
        """
        user_dict = {
            u.id: (u.pid, u.group.pid, u.realm.name)
            for u in ezidapp.models.user.User.objects.all().select_related('group', 'realm')
        }
        counter_dict = {}
        last_id_str = ''

        while not self.terminated():
            # log.debug(f'Starting query')

            qs = (
                ezidapp.models.identifier.SearchIdentifier.objects.filter(
                    identifier__gt=last_id_str
                )
                .only('identifier', 'owner_id', 'createTime', 'isTest', 'hasMetadata')
                .order_by('identifier')
            )[:BATCH_SIZE]

            # log.debug(f'QuerySet len={len(qs)}')
            # log.debug(f'last_id_str="{last_id_str}"')

            if not qs:
                break

            for id_model in qs:
                # log.debug(f'id_model="{id_model}"')

                if not id_model.isTest and id_model.owner_id in user_dict:
                    k = (
                        self._timestampToMonth(id_model.createTime),
                        id_model.owner_id,
                        self._identifierType(id_model.identifier),
                        id_model.hasMetadata,
                    )
                    counter_dict[k] = counter_dict.get(k, 0) + 1

                last_id_str = id_model.identifier

        log.debug(f'Updating statistics: {pprint.pformat(counter_dict)}')

        with django.db.transaction.atomic():
            ezidapp.models.statistics.Statistics.objects.all().delete()
            for k, v in counter_dict.items():
                c = ezidapp.models.statistics.Statistics(
                    month=k[0],
                    owner=user_dict[k[1]][0],
                    ownergroup=user_dict[k[1]][1],
                    realm=user_dict[k[1]][2],
                    type=k[2],
                    hasMetadata=k[3],
                    count=v,
                )
                c.full_clean(validate_unique=False)
                c.save(force_insert=True)

    def _sameTimeOfDayDelta(self):
        now = datetime.datetime.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # noinspection PyTypeChecker
        d = django.conf.settings.DAEMONS_STATISTICS_COMPUTE_CYCLE - (now - midnight).total_seconds()
        if d < 0:
            d += 86400
        return d

    def _timestampToMonth(self, t):
        return time.strftime('%Y-%m', time.localtime(t))

    def _identifierType(self, id_str):
        return id_str.split(':')[0].upper()
