#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import ezidapp.models
import ezidapp.models.statistics


def getTable(owner=None, ownergroup=None, realm=None):
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

    def incrementMonth(month):
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
            nextM = incrementMonth(lastM)
            while nextM != m:
                table.append((nextM, {}))
                nextM = incrementMonth(nextM)
        table.append((m, counts[m]))
        lastM = m
    return table
