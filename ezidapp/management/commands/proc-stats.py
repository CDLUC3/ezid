"""Identifier statistics.

To avoid burdening online identifier processing, statistics are
computed periodically by a daemon thread.  We eschew a synchronous,
inline approach to maintaining statistics because identifier changes
can be complex (creation times can change, ownership can change,
even users and groups can change) and tracking the effects of those
changes on statistics would require knowledge of an identifier's
pre-change state, which is not recorded.
"""

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import threading
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
import impl.nog.util


class Command(ezidapp.management.commands.proc_base.AsyncProcessingCommand):
    help = __doc__
    display = 'Statistics'
    name = 'statistics'
    setting = 'DAEMONS_STATISTICS_ENABLED'

    def __init__(self):
        super(Command, self).__init__(__name__)

    def add_arguments(self, parser):
        super().add_arguments(parser)

    def handle_daemon(self, *_, **opt):
        pass

    def _sameTimeOfDayDelta(self):
        now = self.now()()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # noinspection PyTypeChecker
        d = self._computeCycle - (now - midnight).total_seconds()
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
                for u in ezidapp.models.user.User.objects.all().select_related(
                    "group", "realm"
                )
            }
            counts = {}
            lastIdentifier = ""
            while True:
                qs = (
                    ezidapp.models.identifier.Identifier.objects.filter(
                        identifier__gt=lastIdentifier
                    )
                    .only(
                        "identifier", "owner_id", "createTime", "isTest", "hasMetadata"
                    )
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
            log.exception(' Exception as e')
            self.otherError("stats.recomputeStatistics", e)

    def run(self):
        if self._computeSameTimeOfDay:
            django.db.connections["default"].close()
            django.db.connections["search"].close()
            time.sleep(self._sameTimeOfDayDelta())
        else:
            # We arbitrarily sleep 10 minutes to avoid putting a burden on the
            # server near startup or reload.
            time.sleep(600)
        while (
            django.conf.settings.CROSSREF_ENABLED
            and threading.currentThread().getName() == self._threadName
        ):
            start = time.time()
            self.recomputeStatistics()
            django.db.connections["default"].close()
            django.db.connections["search"].close()
            if self._computeSameTimeOfDay:
                time.sleep(self._sameTimeOfDayDelta())
            else:
                # noinspection PyTypeChecker
                time.sleep(max(self._computeCycle - (time.time() - start), 0))

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

    def getTable(self, owner=None, ownergroup=None, realm=None):
        """Return a table (a list) of identifier counts ordered by month. Each
        element of the list is a pair.

          (month, { (type, hasMetadata): count, ... })

        For example:

           ("2016-01", { ("ARK", False): 14837, ("ARK", True): 1789,
             ("DOI", "True"): 11267 })

        In dictionaries zero counts are not represented, and thus
        dictionaries will not necessarily be complete with respect to the
        Cartesian product of identifier type and hasMetadata.  The range of
        months returned is determined by the range of nonzero counts, but
        within that range months are guaranteed to be consecutive.  Empty
        entries will resemble:

           ("2016-02", {})

        The table can optionally be limited by owner and/or group and/or
        realm.
        """
        qs = ezidapp.models.statistics.Statistics.objects
        if owner is None and ownergroup is None and realm is None:
            qs = qs.all()
        else:
            if owner is not None:
                qs = qs.filter(owner=owner)
            if ownergroup is not None:
                qs = qs.filter(ownergroup=ownergroup)
            if realm is not None:
                qs = qs.filter(realm=realm)
        counts = {}
        for c in qs:
            d = counts.get(c.month, {})
            dc = d.get((c.type, c.hasMetadata), 0)
            d[(c.type, c.hasMetadata)] = dc + c.count
            counts[c.month] = d

        def incrementMonth(self, month):
            y, m = [int(c) for c in month.split("-")]
            m += 1
            if m > 12:
                m = 1
                y += 1
            return f"{y:04d}-{m:02d}"

        table = []
        months = list(counts.keys())
        months.sort()
        for m in months:
            if m != months[0]:
                # noinspection PyUnboundLocalVariable,PyUnboundLocalVariable
                nextM = self.incrementMonth(lastM)
                while nextM != m:
                    table.append((nextM, {}))
                    nextM = self.incrementMonth(nextM)
            table.append((m, counts[m]))
            lastM = m
        return table

    _computeCycle = None
    _computeSameTimeOfDay = None
    _threadName = None

    # django.conf.settings.CROSSREF_ENABLED = (
    #     django.conf.settings.DAEMONS_ENABLED
    #     and django.conf.settings.DAEMONS_STATISTICS_ENABLED ! flag removed
    # )
    # if django.conf.settings.CROSSREF_ENABLED:
    #     _computeCycle = int(django.conf.settings.DAEMONS_STATISTICS_COMPUTE_CYCLE)
    #     _computeSameTimeOfDay = (
    #         django.conf.settings.DAEMONS_STATISTICS_COMPUTE_SAME_TIME_OF_DAY
    #     )
    #     _threadName = uuid.uuid1().hex
    #     t = threading.Thread(target=_statisticsDaemon, name=_threadName)
