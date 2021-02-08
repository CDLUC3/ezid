import ezidapp.models
from impl.util2 import _labelMapping


def convertLegacyToExternal(d, convertAgents=True):
    """Converts a legacy metadata dictionary from internal form (i.e., as
    stored in the Noid "egg" binder) to external form (i.e., as returned to
    clients).

    The dictionary is modified in place.  N.B.: if the dictionary is for
    a DOI identifier, this function does *not* add the _shadowedby
    element.
    """
    if "_is" not in d:
        d["_is"] = "public"
    if "_x" not in d:
        d["_x"] = "yes"
    if convertAgents:
        u = ezidapp.models.store_user.getUserByPid(d["_o"])
        if u is not None:
            d["_o"] = u.username
        g = ezidapp.models.store_group.getGroupByPid(d["_g"])
        if g is not None:
            d["_g"] = g.groupname
    if d["_is"] != "public":
        d["_t"] = d["_t1"]
        del d["_t1"]
    for k in list(d.keys()):
        if k in _labelMapping:
            d[_labelMapping[k]] = d[k]
            del d[k]
