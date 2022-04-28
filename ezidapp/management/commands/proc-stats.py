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
import impl.log


log = logging.getLogger(__name__)


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    name = __name__
    setting = 'DAEMONS_STATISTICS_ENABLED'

    def __init__(self):
        super().__init__()

    def run(self):
        if django.conf.settings.DAEMONS_STATISTICS_COMPUTE_SAME_TIME_OF_DAY:
            self.sleep(self._sameTimeOfDayDelta())
        else:
            # We arbitrarily sleep 10 minutes to avoid putting a burden on the
            # server near startup or reload.
            self.sleep(600)

        while not self.terminated():
            start = self.now()
            self.recomputeStatistics()
            if django.conf.settings.DAEMONS_STATISTICS_COMPUTE_SAME_TIME_OF_DAY:
                self.sleep(self._sameTimeOfDayDelta())
            else:
                # noinspection PyTypeChecker
                self.sleep(
                    max(
                        django.conf.settings.DAEMONS_STATISTICS_COMPUTE_CYCLE
                        - (self.now() - start),
                        0,
                    )
                )

    def _sameTimeOfDayDelta(self):
        now = datetime.datetime.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # noinspection PyTypeChecker
        d = django.conf.settings.DAEMONS_STATISTICS_COMPUTE_CYCLE - (now - midnight).total_seconds()
        if d < 0:
            d += 86400
        return d

    def _timestampToMonth(self, t):
        return time.strftime("%Y-%m", time.localtime(t))

    def _identifierType(self, id_str):
        return id_str.split(":")[0].upper()

    def recomputeStatistics(self):
        """Recompute and stores identifier statistics

        The old statistics are completely replaced.
        """
        try:
            users = {
                u.id: (u.pid, u.group.pid, u.realm.name)
                for u in ezidapp.models.user.User.objects.all().select_related("group", "realm")
            }
            counts = {}
            lastIdentifier = ""
            while not self.terminated():
                qs = (
                    ezidapp.models.identifier.Identifier.objects.filter(
                        identifier__gt=lastIdentifier
                    )
                    .only("identifier", "owner_id", "createTime", "isTest", "hasMetadata")
                    .order_by("identifier")
                )
                qs = list(qs[:1000])
                if len(qs) == 0:
                    break
                for id_model in qs:
                    if not id_model.isTest and id_model.owner_id in users:
                        t = (
                            self._timestampToMonth(id_model.createTime),
                            id_model.owner_id,
                            self._identifierType(id_model.identifier),
                            id_model.hasMetadata,
                        )
                        counts[t] = counts.get(t, 0) + 1
                lastIdentifier = qs[-1].identifier
            with django.db.transaction.atomic():
                ezidapp.models.statistics.Statistics.objects.all().delete()
                for t, v in list(counts.items()):
                    c = ezidapp.models.statistics.Statistics(
                        month=t[0],
                        owner=users[t[1]][0],
                        ownergroup=users[t[1]][1],
                        realm=users[t[1]][2],
                        type=t[2],
                        hasMetadata=t[3],
                        count=v,
                    )
                    c.full_clean(validate_unique=False)
                    c.save(force_insert=True)
        except Exception as e:
            log.exception('Exception')
            impl.log.otherError("stats.recomputeStatistics", e)

    def query(
        self,
        month=None,
        owner=None,
        ownergroup=None,
        realm=None,
        type=None,
        hasMetadata=None,
    ):
        """Return the number of identifiers matching a constraint as defined by
        the non-None argument values.

        The arguments correspond to the fields in the Statistics model.
        """
        qs = ezidapp.models.statistics.Statistics.objects
        if month is not None:
            qs = qs.filter(month=month)
        if owner is not None:
            qs = qs.filter(owner=owner)
        if ownergroup is not None:
            qs = qs.filter(ownergroup=ownergroup)
        if realm is not None:
            qs = qs.filter(realm=realm)
        if type is not None:
            qs = qs.filter(type=type)
        if hasMetadata is not None:
            qs = qs.filter(hasMetadata=hasMetadata)
        return qs.aggregate(django.db.models.Sum("count"))["count__sum"] or 0
