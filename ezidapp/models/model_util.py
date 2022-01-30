#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import ezidapp.models.group
import ezidapp.models.util


_labelMapping = {
    "_o": "_owner",
    "_g": "_ownergroup",
    "_c": "_created",
    "_u": "_updated",
    "_t": "_target",
    "_p": "_profile",
    "_is": "_status",
    "_x": "_export",
    "_d": "_datacenter",
    "_cr": "_crossref",
}


def convertLegacyToExternal(d, convertAgents=True):
    """Convert a legacy metadata dictionary from internal form (i.e., as
    stored in the Noid "egg" binder) to external form (i.e., as returned to
    clients).

    The dictionary is modified in place. N.B.: if the dictionary is for
    a DOI identifier, this function does *not* add the _shadowedby
    element.
    """
    if "_is" not in d:
        d["_is"] = "public"
    if "_x" not in d:
        d["_x"] = "yes"
    if convertAgents:
        u = ezidapp.models.util.getUserByPid(d["_o"])
        if u is not None:
            d["_o"] = u.username
        g = ezidapp.models.util.getGroupByPid(d["_g"])
        if g is not None:
            d["_g"] = g.groupname
    if d["_is"] != "public":
        d["_t"] = d["_t1"]
        del d["_t1"]
    for k in list(d.keys()):
        if k in _labelMapping:
            d[_labelMapping[k]] = d[k]
            del d[k]
