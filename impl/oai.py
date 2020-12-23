# =============================================================================
#
# EZID :: oai.py
#
# Support for OAI-PMH 2.0
# <http://www.openarchives.org/OAI/openarchivesprotocol.html>.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2014, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.conf
import django.db.models
import django.http
import hashlib
import lxml.etree
import time

from . import config
from . import datacite
import ezidapp.models
from . import util

_enabled = None
_baseUrl = None
_repositoryName = None
_adminEmail = None
_batchSize = None


def loadConfig():
    global _enabled, _baseUrl, _repositoryName, _adminEmail, _batchSize
    _enabled = config.get("oai.enabled").lower() == "true"
    _baseUrl = config.get("DEFAULT.ezid_base_url")
    _repositoryName = config.get("oai.repository_name")
    _adminEmail = config.get("oai.admin_email")
    _batchSize = int(config.get("oai.batch_size"))


def _q(elementName):
    return "{http://www.openarchives.org/OAI/2.0/}" + elementName


def _parseTime(s):
    try:
        return util.parseTimestampZulu(s, True)
    except:
        return None


def _buildResponse(oaiRequest, body):
    root = lxml.etree.Element(
        _q("OAI-PMH"), nsmap={None: "http://www.openarchives.org/OAI/2.0/"}
    )
    root.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"] = (
        "http://www.openarchives.org/OAI/2.0/ "
        + "http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd"
    )
    root.addprevious(
        lxml.etree.ProcessingInstruction(
            "xml-stylesheet", "type='text/xsl' href='/static/stylesheets/oai2.xsl'"
        )
    )
    lxml.etree.SubElement(root, _q("responseDate")).text = util.formatTimestampZulu(
        int(time.time())
    )
    e = lxml.etree.SubElement(root, _q("request"))
    e.text = _baseUrl + "/oai"
    if not body.tag.endswith("}error") or body.attrib["code"] not in [
        "badVerb",
        "badArgument",
    ]:
        e.attrib["verb"] = oaiRequest[0]
        for k, v in list(oaiRequest[1].items()):
            e.attrib[k] = v
    root.append(body)
    return lxml.etree.tostring(
        root.getroottree(), encoding="UTF-8", xml_declaration=True
    )


def _error(oaiRequest, code, message=None):
    e = lxml.etree.Element(_q("error"))
    e.attrib["code"] = code
    if message != None:
        e.text = message
    return _buildResponse(oaiRequest, e)


_arguments = {
    # verb: { argument: R (required), O (optional), X (exclusive) }
    "GetRecord": {"identifier": "R", "metadataPrefix": "R"},
    "Identify": {},
    "ListIdentifiers": {
        "metadataPrefix": "R",
        "from": "O",
        "until": "O",
        "set": "O",
        "resumptionToken": "X",
    },
    "ListMetadataFormats": {"identifier": "O"},
    "ListRecords": {
        "metadataPrefix": "R",
        "from": "O",
        "until": "O",
        "set": "O",
        "resumptionToken": "X",
    },
    "ListSets": {"resumptionToken": "X"},
}


def _buildRequest(request):
    if request.method == "GET":
        REQUEST = request.GET
    else:
        REQUEST = request.POST
    if len(REQUEST.getlist("verb")) != 1:
        return _error(None, "badVerb", "no verb or multiple verbs")
    verb = REQUEST["verb"]
    if verb not in _arguments:
        return _error(None, "badVerb", "illegal verb")
    r = (verb, {})
    exclusive = False
    for k in REQUEST:
        if k == "verb":
            continue
        if k not in _arguments[verb]:
            return _error(None, "badArgument", "illegal argument: " + k)
        if len(REQUEST.getlist(k)) > 1:
            return _error(None, "badArgument", "multiple values for argument: " + k)
        if _arguments[verb][k] == "X":
            if len(list(REQUEST.keys())) > 2:
                return _error(None, "badArgument", "argument is not exclusive: " + k)
            exclusive = True
        r[1][k] = REQUEST[k]
    if not exclusive:
        for k, rox in list(_arguments[verb].items()):
            if rox == "R" and k not in r[1]:
                return _error(None, "badArgument", "missing required argument: " + k)
    return r


def _buildResumptionToken(from_, until, prefix, cursor, total):
    # The semantics of a resumption token: return identifiers whose
    # update times are in the range (from_, until].  'until' may be None.
    if until is not None:
        until = str(until)
    else:
        until = ""
    hash = hashlib.sha1(
        "%d,%s,%s,%d,%d,%s"
        % (from_, until, prefix, cursor, total, django.conf.settings.SECRET_KEY)
    ).hexdigest()[::4]
    return "%d,%s,%s,%d,%d,%s" % (from_, until, prefix, cursor, total, hash)


def _unpackResumptionToken(token):
    try:
        from_, until, prefix, cursor, total, hash1 = token.split(",")
        hash2 = hashlib.sha1(
            "%s,%s,%s,%s,%s,%s"
            % (from_, until, prefix, cursor, total, django.conf.settings.SECRET_KEY)
        ).hexdigest()[::4]
        assert hash1 == hash2
        if len(until) > 0:
            until = int(until)
        else:
            until = None
        return (int(from_), until, prefix, int(cursor), int(total))
    except:
        return None


def _buildDublinCoreRecord(identifier):
    root = lxml.etree.Element(
        "{http://www.openarchives.org/OAI/2.0/oai_dc/}dc",
        nsmap={
            "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
            "dc": "http://purl.org/dc/elements/1.1/",
        },
    )
    root.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"] = (
        "http://www.openarchives.org/OAI/2.0/oai_dc/ "
        + "http://www.openarchives.org/OAI/2.0/oai_dc.xsd"
    )

    def q(elementName):
        return "{http://purl.org/dc/elements/1.1/}" + elementName

    lxml.etree.SubElement(root, q("identifier")).text = identifier.identifier
    km = identifier.kernelMetadata()
    for e in ["creator", "title", "publisher", "date", "type"]:
        if getattr(km, e) != None:
            # Adding a try catch block to generate XML
            try:
                # Generate XML node text from the arrtibute value
                lxml.etree.SubElement(root, q(e)).text = getattr(km, e)
            except:
                # Function "sanitizeXmlSafeCharset" returns a copy of the given Unicode string
                # in which characters not accepted by XML 1.1 have been replaced with spaces.
                lxml.etree.SubElement(root, q(e)).text = util.sanitizeXmlSafeCharset(
                    getattr(km, e)
                ).strip()
    return root


def _doGetRecord(oaiRequest):
    id = util.normalizeIdentifier(oaiRequest[1]["identifier"])
    if id == None:
        return _error(oaiRequest, "idDoesNotExist")
    try:
        identifier = ezidapp.models.SearchIdentifier.objects.get(identifier=id)
    except ezidapp.models.SearchIdentifier.DoesNotExist:
        return _error(oaiRequest, "idDoesNotExist")
    if not identifier.oaiVisible:
        return _error(oaiRequest, "idDoesNotExist")
    if oaiRequest[1]["metadataPrefix"] == "oai_dc":
        me = _buildDublinCoreRecord(identifier)
    elif oaiRequest[1]["metadataPrefix"] == "datacite":
        me = datacite.upgradeDcmsRecord(
            identifier.dataciteMetadata(), returnString=False
        )
    else:
        return _error(oaiRequest, "cannotDisseminateFormat")
    root = lxml.etree.Element(_q("GetRecord"))
    r = lxml.etree.SubElement(root, _q("record"))
    h = lxml.etree.SubElement(r, _q("header"))
    lxml.etree.SubElement(h, _q("identifier")).text = oaiRequest[1]["identifier"]
    lxml.etree.SubElement(h, _q("datestamp")).text = util.formatTimestampZulu(
        identifier.updateTime
    )
    lxml.etree.SubElement(r, _q("metadata")).append(me)
    return _buildResponse(oaiRequest, root)


def _doIdentify(oaiRequest):
    e = lxml.etree.Element(_q("Identify"))
    lxml.etree.SubElement(e, _q("repositoryName")).text = _repositoryName
    lxml.etree.SubElement(e, _q("baseURL")).text = _baseUrl + "/oai"
    lxml.etree.SubElement(e, _q("protocolVersion")).text = "2.0"
    lxml.etree.SubElement(e, _q("adminEmail")).text = _adminEmail
    t = ezidapp.models.SearchIdentifier.objects.filter(oaiVisible=True).aggregate(
        django.db.models.Min("updateTime")
    )["updateTime__min"]
    if t == None:
        t = 0
    lxml.etree.SubElement(e, _q("earliestDatestamp")).text = util.formatTimestampZulu(t)
    lxml.etree.SubElement(e, _q("deletedRecord")).text = "no"
    lxml.etree.SubElement(e, _q("granularity")).text = "YYYY-MM-DDThh:mm:ssZ"
    return _buildResponse(oaiRequest, e)


def _doHarvest(oaiRequest, batchSize, includeMetadata):
    if "resumptionToken" in oaiRequest[1]:
        r = _unpackResumptionToken(oaiRequest[1]["resumptionToken"])
        if r == None:
            return _error(oaiRequest, "badResumptionToken")
        from_, until, prefix, cursor, total = r
    else:
        prefix = oaiRequest[1]["metadataPrefix"]
        if prefix not in ["oai_dc", "datacite"]:
            return _error(oaiRequest, "cannotDisseminateFormat")
        if "set" in oaiRequest[1]:
            return _error(oaiRequest, "noSetHierarchy")
        if "from" in oaiRequest[1]:
            from_ = _parseTime(oaiRequest[1]["from"])
            if from_ == None:
                return _error(oaiRequest, "badArgument", "illegal 'from' UTCdatetime")
            # In OAI-PMH, from_ is inclusive, but for us it's exclusive, ergo...
            from_ -= 1
        else:
            from_ = 0
        if "until" in oaiRequest[1]:
            until = _parseTime(oaiRequest[1]["until"])
            if until == None:
                return _error(oaiRequest, "badArgument", "illegal 'until' UTCdatetime")
            if "from" in oaiRequest[1]:
                if len(oaiRequest[1]["from"]) != len(oaiRequest[1]["until"]):
                    return _error(
                        oaiRequest,
                        "badArgument",
                        "incommensurate UTCdatetime granularities",
                    )
                if from_ >= until:
                    return _error(oaiRequest, "badArgument", "'until' precedes 'from'")
        else:
            until = None
        cursor = 0
        total = None
    q = ezidapp.models.SearchIdentifier.objects.filter(oaiVisible=True).filter(
        updateTime__gt=from_
    )
    if until != None:
        q = q.filter(updateTime__lte=until)
    q = q.select_related("profile").order_by("updateTime")
    ids = list(q[:batchSize])
    # Note a bug in the protocol itself: if a resumption token was
    # supplied, we are required to return a (possibly empty) token, but
    # the only way to return a resumption token is to return at least
    # one record.  By design, if we receive a resumption token there
    # should be at least one record remaining, no problemo.  But interim
    # database modifications can cause there to be none, in which case
    # we are left with no legal response.
    if len(ids) == 0:
        return _error(oaiRequest, "noRecordsMatch")
    # Our algorithm is as follows.  If we received fewer records than we
    # requested, then the harvest must be complete.  Otherwise, there
    # may be more records.  In that case, let T be the update time of
    # the last identifier received, and let I be the last identifier
    # received whose update time strictly precedes T.  Then in this
    # batch we return identifiers up through and including I, and use
    # I's update time as the exclusive lower bound in the new resumption
    # token.  Identifier update times in EZID are almost (but not quite)
    # unique, and hence if the batch size is 100 we will typically
    # return 99 identifiers; the 100th identifier will be returned as
    # the first identifier in the next request.  What if every
    # identifier in the batch has update time T?  Realistically that has
    # no chance of happening, but for theoretical purity we repeat the
    # process using a larger batch size.  In the limiting case the batch
    # size would get so large that it would encompass every remaining
    # identifier.
    if len(ids) == batchSize:
        last = None
        for i in range(len(ids) - 2, -1, -1):
            if ids[i].updateTime < ids[-1].updateTime:
                last = i
                break
        if last == None:
            # Truly exceptional case.
            return _doHarvest(oaiRequest, batchSize * 2, includeMetadata)
    else:
        last = len(ids) - 1
    e = lxml.etree.Element(_q(oaiRequest[0]))
    for i in range(last + 1):
        if includeMetadata:
            r = lxml.etree.SubElement(e, _q("record"))
            h = lxml.etree.SubElement(r, _q("header"))
        else:
            h = lxml.etree.SubElement(e, _q("header"))
        lxml.etree.SubElement(h, _q("identifier")).text = ids[i].identifier
        lxml.etree.SubElement(h, _q("datestamp")).text = util.formatTimestampZulu(
            ids[i].updateTime
        )
        if includeMetadata:
            if prefix == "oai_dc":
                me = _buildDublinCoreRecord(ids[i])
            elif prefix == "datacite":
                me = datacite.upgradeDcmsRecord(
                    ids[i].dataciteMetadata(), returnString=False
                )
            else:
                assert False, "unhandled case"
            lxml.etree.SubElement(r, _q("metadata")).append(me)
    if "resumptionToken" in oaiRequest[1] or len(ids) == batchSize:
        if total == None:
            total = q.count()
        rt = lxml.etree.SubElement(e, _q("resumptionToken"))
        rt.attrib["cursor"] = str(cursor)
        rt.attrib["completeListSize"] = str(total)
        if len(ids) == batchSize:
            rt.text = _buildResumptionToken(
                ids[last].updateTime, until, prefix, cursor + last + 1, total
            )
    return _buildResponse(oaiRequest, e)


def _doListMetadataFormats(oaiRequest):
    e = lxml.etree.Element(_q("ListMetadataFormats"))
    mf = lxml.etree.SubElement(e, _q("metadataFormat"))
    lxml.etree.SubElement(mf, _q("metadataPrefix")).text = "oai_dc"
    lxml.etree.SubElement(
        mf, _q("schema")
    ).text = "http://www.openarchives.org/OAI/2.0/oai_dc.xsd"
    lxml.etree.SubElement(
        mf, _q("metadataNamespace")
    ).text = "http://www.openarchives.org/OAI/2.0/oai_dc/"
    mf = lxml.etree.SubElement(e, _q("metadataFormat"))
    lxml.etree.SubElement(mf, _q("metadataPrefix")).text = "datacite"
    lxml.etree.SubElement(
        mf, _q("schema")
    ).text = "http://schema.datacite.org/meta/kernel-4/metadata.xsd"
    lxml.etree.SubElement(
        mf, _q("metadataNamespace")
    ).text = "http://datacite.org/schema/kernel-4"
    return _buildResponse(oaiRequest, e)


def _doListSets(oaiRequest):
    if "resumptionToken" in oaiRequest[1]:
        return _error(oaiRequest, "badResumptionToken")
    else:
        return _error(oaiRequest, "noSetHierarchy")


def dispatch(request):
    """
  OAI-PMH request dispatcher.
  """
    if not _enabled:
        return django.http.HttpResponse(
            "service unavailable", status=503, content_type="text/plain"
        )
    if request.method not in ["GET", "POST"]:
        return django.http.HttpResponse(
            "method not allowed", status=405, content_type="text/plain"
        )
    oaiRequest = _buildRequest(request)
    if type(oaiRequest) is str:
        r = oaiRequest
    else:
        if oaiRequest[0] == "GetRecord":
            r = _doGetRecord(oaiRequest)
        elif oaiRequest[0] == "Identify":
            r = _doIdentify(oaiRequest)
        elif oaiRequest[0] == "ListIdentifiers":
            r = _doHarvest(oaiRequest, _batchSize, includeMetadata=False)
        elif oaiRequest[0] == "ListMetadataFormats":
            r = _doListMetadataFormats(oaiRequest)
        elif oaiRequest[0] == "ListRecords":
            r = _doHarvest(oaiRequest, _batchSize, includeMetadata=True)
        elif oaiRequest[0] == "ListSets":
            r = _doListSets(oaiRequest)
        else:
            assert False, "unhandled case"
    response = django.http.HttpResponse(r, content_type="text/xml; charset=UTF-8")
    response["Content-Length"] = len(r)
    return response
