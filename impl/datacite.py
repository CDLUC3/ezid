#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Interface to the DataCite Metadata Store <https://mds.datacite.org/>
operated by the Technische Informationsbibliothek (TIB)
<http://www.tib.uni-hannover.de/>.
"""

import http.client
import logging
import os
import os.path
import re
import threading
import time
import typing
import urllib.error
import urllib.parse
import urllib.request
import urllib.response

import django.conf
import lxml.etree
import xmltodict

import ezidapp.models.shoulder
import ezidapp.models.validation
import impl.mapping
import impl.util

log = logging.getLogger(__name__)

ALLOCATOR_DICT = {
    a: getattr(django.conf.settings, f"ALLOCATOR_{a}_PASSWORD")
    for a in django.conf.settings.DATACITE_ALLOCATORS.split(",")
}

SCHEMA_DICT = {}
for f in os.listdir(os.path.join(django.conf.settings.PROJECT_ROOT, "xsd")):
    m = re.match("datacite-kernel-(.*)", f)
    if m:
        SCHEMA_DICT[m.group(1)] = (
            lxml.etree.XMLSchema(
                lxml.etree.parse(
                    os.path.join(django.conf.settings.PROJECT_ROOT, "xsd", f, "metadata.xsd")
                )
            ),
            threading.Lock(),
        )

_SCHEMAS_DICT = SCHEMA_DICT

_SCHEMA_VERSION_RE = re.compile("{http://datacite\\.org/schema/kernel-([^}]*)}resource$")

PROLOG_RE: typing.Pattern[str] = re.compile(
    '(<\\?xml\\s+version\\s*=\\s*[\'"]([-\\w.:]+)["\'])'
    '(\\s+encoding\\s*=\\s*[\'"]([-\\w.]+)["\'])?'
)
UTF8_RE = re.compile("UTF-?8$", re.I)
ROOT_TAG_RE = re.compile("{(http://datacite\\.org/schema/kernel-([^}]*))}resource$")

METADATA_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<resource xmlns="http://datacite.org/schema/kernel-4"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://datacite.org/schema/kernel-4
    http://schema.datacite.org/meta/kernel-4/metadata.xsd">
  <identifier identifierType="{}">{}</identifier>
  <creators>
    <creator>
      <creatorName>{}</creatorName>
    </creator>
  </creators>
  <titles>
    <title>{}</title>
  </titles>
  <publisher>{}</publisher>
  <publicationYear>{}</publicationYear>
"""

RESOURCE_TYPE_TEMPLATE_1 = """  <resourceType resourceTypeGeneral="{}"/>
"""

RESOURCE_TYPE_TEMPLATE_2 = """  <resourceType resourceTypeGeneral="{}">{}</resourceType>
"""


class _HTTPErrorProcessor(urllib.request.HTTPErrorProcessor):
    def http_response(self, request, response: http.client.HTTPResponse):
        # Bizarre that Python considers this an error.
        # TODO: Check if this is still required
        if response.status == 201:
            return response
        else:
            return super().http_response(request, response)

    https_response = http_response


def registerIdentifier(doi, targetUrl, datacenter=None):
    """Register a scheme-less DOI identifier (e.g., "10.5060/FOO") and target
    URL (e.g., "http://whatever...") with DataCite

    Args:
        doi:
        targetUrl:
        datacenter: If specified, should be the identifier's datacenter, e.g.,
            "CDL.BUL".

    Returns:
        There are three possible returns: None on success; a string error message if the
        target URL was not accepted by DataCite; or a thrown exception on other error.
    """
    if not django.conf.settings.DATACITE_ENABLED:
        return None
    # To deal with transient problems with the Handle system underlying
    # the DataCite service, we make multiple attempts.
    for i in range(django.conf.settings.DATACITE_NUM_ATTEMPTS):
        o = urllib.request.build_opener(_HTTPErrorProcessor)

        data = "doi={}\nurl={}".format(
            doi.replace('\\', r'\\'),
            targetUrl.replace("\\", r'\\'),
        ).encode("utf-8")

        r = urllib.request.Request(django.conf.settings.DATACITE_DOI_URL, data=data)
        # We manually supply the HTTP Basic authorization header to avoid
        # the doubling of the number of HTTP transactions caused by the
        # challenge/response model.
        r.add_header("Authorization", _authorization(doi, datacenter))
        r.add_header("Content-Type", "text/plain; charset=utf-8")

        c = None
        try:
            c = o.open(r, timeout=django.conf.settings.DATACITE_TIMEOUT)
            body_str = c.read().decode('utf-8', errors='replace')
            assert body_str == "OK", f"Unexpected return from DataCite register DOI operation: {body_str}"
        except urllib.error.HTTPError as e:
            log.debug(f'registerIdentifier() failed: {str(e)}')
            body_str = e.fp.read().decode('utf-8', errors='replace')
            if e.code == 400 and body_str.startswith("[url]"):
                return body_str
            if e.code != 500 or i == django.conf.settings.DATACITE_NUM_ATTEMPTS - 1:
                raise e
        except Exception:
            if i == django.conf.settings.DATACITE_NUM_ATTEMPTS - 1:
                raise
        else:
            break
        finally:
            if c:
                c.close()
        # increase reattempt delay as a magnitude of DATACITE_NUM_ATTEMPTS
        time.sleep(django.conf.settings.DATACITE_REATTEMPT_DELAY + (60 * (i + 1)))
    return None


def setTargetUrl(doi, targetUrl, datacenter=None):
    """Set the target URL of an existing scheme-less DOI identifier (e.g.,
    "10.5060/FOO")

    Args:
        doi:
        targetUrl:
        datacenter: If specified, should be the identifier's datacenter, e.g.,
            "CDL.BUL".

    Returns:
        There are three possible returns: None on success; a string error message if the
        target URL was not accepted by DataCite; or a thrown exception on other error.
    """
    return registerIdentifier(doi, targetUrl, datacenter)


def getTargetUrl(doi, datacenter=None):
    """
    Args:
        doi:
        datacenter: If specified, should be the identifier's datacenter, e.g.,
        "CDL.BUL".

    Returns:
        The target URL of a scheme-less DOI identifier (e.g., "10.5060/FOO") as
        registered with DataCite, or None if the identifier is not registered.
    """
    # To hide transient network errors, we make multiple attempts.
    for i in range(django.conf.settings.DATACITE_NUM_ATTEMPTS):
        o = urllib.request.build_opener(_HTTPErrorProcessor)
        r = urllib.request.Request(
            django.conf.settings.DATACITE_DOI_URL + "/" + urllib.parse.quote(doi)
        )
        # We manually supply the HTTP Basic authorization header to avoid
        # the doubling of the number of HTTP transactions caused by the
        # challenge/response model.
        r.add_header("Authorization", _authorization(doi, datacenter))
        c = None
        try:
            c = o.open(r, timeout=django.conf.settings.DATACITE_TIMEOUT)
            return c.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code != 500 or i == django.conf.settings.DATACITE_NUM_ATTEMPTS - 1:
                raise e
        except Exception:
            if i == django.conf.settings.DATACITE_NUM_ATTEMPTS - 1:
                raise
        finally:
            if c:
                c.close()
        # increase reattempt delay as a magnitude of DATACITE_NUM_ATTEMPTS
        time.sleep(django.conf.settings.DATACITE_REATTEMPT_DELAY + (60 * (i + 1)))


def validateDcmsRecord(identifier, record, schemaValidate=True):
    """Validate and normalize a DataCite Metadata Scheme

    Args:
        identifier: <http://schema.datacite.org/> record for a qualified identifier
            (e.g., "doi:10.5060/FOO").
        record:
            The record should be unencoded. The record is normalized by removing any
            encoding declaration; by converting from deprecated schema versions if
            necessary; and by inserting an appropriate 'schemaLocation' attribute.
            Also, 'identifier' is inserted in the returned record.
        schemaValidate:
            If true, the record is validated against the appropriate XML schema;
            otherwise, only a more forgiving well- formedness check is performed. (In
            an extension to DCMS, we allow the identifier to be something other than a
            DOI, for example, an ARK.)

    Returns:
        Either the normalized record is returned or an assertion error is raised.
    """
    m = PROLOG_RE.match(record)
    if m:
        assert m.group(2) == "1.0", "Unsupported XML version"
        if m.group(3) is not None:
            assert UTF8_RE.match(m.group(4)), "XML encoding must be UTF-8"
            record = record[: len(m.group(1))] + record[len(m.group(1)) + len(m.group(3)) :]
    else:
        record = '<?xml version="1.0"?>\n' + record
    # We first do an initial parsing of the record to check
    # well-formedness and to be able to manipulate it, but hold off on
    # full schema validation because of our extension to the schema to
    # include other identifier types.
    try:
        root = lxml.etree.XML(record)
    except Exception as e:
        assert False, "XML parse error: " + str(e)
    m = ROOT_TAG_RE.match(root.tag)
    assert m, "Not a DataCite record"
    version = m.group(2)
    # Report error if schema versions have been deprecated by DataCite.
    if version in ["2.1", "2.2", "3"]:
        assert False, "DataCite schema version {} is deprecated".format(version)
    schema = _SCHEMAS_DICT.get(version, None)
    assert schema is not None, "Unsupported DataCite record version"
    i = root.xpath("N:identifier", namespaces={"N": m.group(1)})
    assert (
        len(i) == 1 and "identifierType" in i[0].attrib
    ), "Malformed DataCite record: no <identifier> element"
    i = i[0]
    if identifier.startswith("doi:"):
        type = "DOI"
        identifier = identifier[4:]
    elif identifier.startswith("ark:/"):
        type = "ARK"
        identifier = identifier[5:]
    elif identifier.startswith("uuid:"):
        type = "UUID"
        identifier = identifier[5:]
    else:
        assert False, "Unrecognized identifier scheme"
    assert (
        i.attrib["identifierType"] == type
    ), "Mismatch between identifier type and <identifier> element"
    if schemaValidate:
        # We temporarily replace the identifier with something innocuous
        # that will pass the schema's validation check, then change it
        # back. Locking lameness: despite its claims, XMLSchema objects
        # are in fact not threadsafe.
        i.attrib["identifierType"] = "DOI"
        i.text = "10.1234/X"
        schema[1].acquire()
        try:
            schema[0].assertValid(root)
        except Exception as e:
            # Ouch. On some LXML installations, but not all, an error is
            # "sticky" and, unless it is cleared out, will be returned
            # repeatedly regardless of what new error is encountered.
            # noinspection PyProtectedMember
            schema[0]._clear_error_log()
            # LXML error messages may contain snippets from the source
            # document, and hence may contain Unicode characters. We're
            # really not set up to propagate such characters through
            # exceptions and so replace them. Too, the presence of such
            # characters can be the source of the problem, so explicitly
            # exposing them can be a help.
            raise AssertionError(repr(e))
        finally:
            schema[1].release()
        i.attrib["identifierType"] = type
    i.text = identifier
    root.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"] = (
        "http://datacite.org/schema/kernel-{} "
        "http://schema.datacite.org/meta/kernel-{}/metadata.xsd"
    ).format(version, version)
    try:
        # We re-sanitize the document because unacceptable characters can
        # be (and have been) introduced via XML character entities.
        return '<?xml version="1.0"?>\n' + impl.util.sanitizeXmlSafeCharset(
            lxml.etree.tostring(root, encoding=str)
        )
    except Exception as e:
        assert False, "XML serialization error: " + str(e)


def formRecord(identifier, metadata, supplyMissing=False, profile=None):
    """Form an XML record for upload to DataCite, employing metadata mapping if
    necessary

    Args:
        identifier: should be a qualified identifier (e.g., "doi:10.5060/FOO").
        metadata: should be the identifier's metadata as a dictionary of (name, value)
            pairs.
        supplyMissing: If True, the "(:unav)" code is supplied for missing required
            metadata fields; otherwise, missing metadata results in an assertion error
            being raised.
        profile: The metadata profile to use for the mapping; if None, the profile is
            determined from any _profile or _p field in the metadata dictionary and
            otherwise defaults to "erc".

    Returns:
        Returns an XML document as a Unicode string. The document contains a UTF-8
        encoding declaration, but is not in fact encoded.
    """

    def _interpolate(template, *args):
        return template.format(*tuple(impl.util.xmlEscape(a) for a in args))

    if identifier.startswith("doi:"):
        idType = "DOI"
        idBody = identifier[4:]
    elif identifier.startswith("ark:/"):
        idType = "ARK"
        idBody = identifier[5:]
    elif identifier.startswith("uuid:"):
        idType = "UUID"
        idBody = identifier[5:]
    else:
        assert False, "unhandled case"
    if profile is None:
        profile = metadata.get("_p", metadata.get("_profile", "erc"))
    if metadata.get("datacite", "").strip() != "":
        return impl.util.insertXmlEncodingDeclaration(metadata["datacite"])
    elif profile == "crossref" and metadata.get("crossref", "").strip() != "":
        # We could run Crossref metadata through the metadata mapper using
        # the case below, but doing it this way creates a richer XML
        # record.
        overrides = {"_idType": idType, "_id": idBody}
        for e in ["creator", "title", "publisher", "publicationyear", "resourcetype"]:
            if metadata.get("datacite." + e, "").strip() != "":
                overrides["datacite." + e] = metadata["datacite." + e].strip()
        if "datacite.publicationyear" in overrides:
            try:
                overrides["datacite.publicationyear"] = ezidapp.models.validation.publicationDate(
                    overrides["datacite.publicationyear"]
                )[:4]
            except Exception:
                overrides["datacite.publicationyear"] = "0000"
        try:
            return impl.util.insertXmlEncodingDeclaration(
                crossrefToDatacite(metadata["crossref"].strip(), overrides)
            )
        except Exception as e:
            assert False, "Crossref to DataCite metadata conversion error: " + str(e)
    else:
        km = impl.mapping.map(metadata, datacitePriority=True, profile=profile)
        for a in ["creator", "title", "publisher", "date"]:
            if getattr(km, a) is None:
                if supplyMissing:
                    setattr(km, a, "(:unav)")
                else:
                    assert False, "no " + ("publication date" if a == "date" else a)
        d = km.validatedDate
        r = _interpolate(
            METADATA_TEMPLATE,
            idType,
            idBody,
            km.creator,
            km.title,
            km.publisher,
            d[:4] if d else "0000",
        )
        t = km.validatedType
        if t is None:
            if km.type is not None:
                t = "Other"
            else:
                t = "Other/(:unav)"
        if "/" in t:
            gt, st = t.split("/", 1)
            r += _interpolate(RESOURCE_TYPE_TEMPLATE_2, gt, st)
        else:
            r += _interpolate(RESOURCE_TYPE_TEMPLATE_1, t)
        r += "</resource>\n"
        return r


def uploadMetadata(doi, current, delta, forceUpload=False, datacenter=None):
    """Upload citation metadata for the resource identified by an existing scheme-less
    DOI identifier (e.g., "10.5060/FOO") to DataCite.

    This same function can be used to overwrite previously-uploaded metadata.

    Args:
        doi:

        current:
        delta:
            Should be dictionaries mapping metadata element names (e.g.,
            "Title") to values. 'current+delta' is uploaded, but only if there is at
            least one DataCite-relevant difference between it and 'current' alone
            (unless 'forceUpload' is true).

        forceUpload:
        datacenter: If specified, should be the identifier datacenter, e.g.,
            "CDL.BUL".

    Returns:
        There are three possible returns:
            - None on success
            - A string error message if the uploaded DataCite Metadata Scheme record was
              not accepted by DataCite (due to an XML-related problem)
            - A thrown exception on other error. No error checking is done on the inputs.
    """
    try:
        oldRecord = formRecord("doi:" + doi, current)
    except AssertionError:
        oldRecord = None
    m = current.copy()
    m.update(delta)
    try:
        newRecord = formRecord("doi:" + doi, m)
    except AssertionError as e:
        return "DOI metadata requirements not satisfied: " + str(e)
    if newRecord == oldRecord and not forceUpload:
        return None
    if not django.conf.settings.DATACITE_ENABLED:
        return None
    # To hide transient network errors, we make multiple attempts.
    for i in range(django.conf.settings.DATACITE_NUM_ATTEMPTS):
        o = urllib.request.build_opener(_HTTPErrorProcessor)
        r = urllib.request.Request(django.conf.settings.DATACITE_METADATA_URL)
        # We manually supply the HTTP Basic authorization header to avoid
        # the doubling of the number of HTTP transactions caused by the
        # challenge/response model.
        r.add_header("Authorization", _authorization(doi, datacenter))
        r.add_header("Content-Type", "application/xml; charset=utf-8")
        r.data = newRecord.encode("utf-8")
        c = None
        try:
            c = o.open(r, timeout=django.conf.settings.DATACITE_TIMEOUT)
            body_str = c.read().decode('utf-8', errors='replace')
            assert body_str.startswith("OK"), (
                f"unexpected return from DataCite store metadata operation: {body_str}"
            )
        except urllib.error.HTTPError as e:
            message = e.fp.read().decode('utf-8', errors='replace')
            log.error(f'{str(e)}: {message}')
            if e.code in (400, 422):
                return f"element 'datacite': {message}"
            if e.code != 500 or i == django.conf.settings.DATACITE_NUM_ATTEMPTS - 1:
                raise e
        except Exception:
            if i == django.conf.settings.DATACITE_NUM_ATTEMPTS - 1:
                raise
        else:
            return None
        finally:
            if c:
                c.close()
        # increase reattempt delay as a magnitude of DATACITE_NUM_ATTEMPTS
        time.sleep(django.conf.settings.DATACITE_REATTEMPT_DELAY + (60 * (i + 1)))


def deactivateIdentifier(doi, datacenter=None):
    """Deactivate an existing, scheme-less DOI identifier (e.g., "10.5060/FOO") in
    DataCite.

    Args:
        doi:
        datacenter: 'datacenter', if specified, should be the identifier's datacenter,
            e.g., "CDL.BUL".

    Returns:
        Returns None; raises an exception on error.

    This removes the identifier from dataCite's search index, but has no effect on the
    identifier's existence in the Handle system or on the ability to change the
    identifier's target URL. The identifier can and will be reactivated by uploading
    new metadata to it (cf. uploadMetadata in this module).
    """
    if not django.conf.settings.DATACITE_ENABLED:
        return
    try:
        _deactivate(doi, datacenter)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # The identifier must already have metadata in DataCite; in case
            # it doesn't (as may be the case with legacy identifiers),
            # upload some bogus metadata.
            message = uploadMetadata(
                doi,
                {},
                {
                    "datacite.title": "inactive",
                    "datacite.creator": "inactive",
                    "datacite.publisher": "inactive",
                    "datacite.publicationyear": "0000",
                },
                datacenter=datacenter,
            )
            assert message is None, (
                "Unexpected return from DataCite store metadata operation: " + message
            )
            _deactivate(doi, datacenter)
        else:
            raise
    return None


def ping():
    """Test the DataCite API (as well as the underlying Handle System)

    Returns:
        "up" or "down".
    """
    if not django.conf.settings.DATACITE_ENABLED:
        return "up"
    try:
        r = setTargetUrl(
            django.conf.settings.DATACITE_PING_DOI,
            django.conf.settings.DATACITE_PING_TARGET,
            django.conf.settings.DATACITE_PING_DATACENTER,
        )
        assert r is None
    except Exception:
        return "down"
    else:
        return "up"


def pingDataciteOnly():
    """Test the DataCite API (only)

    Returns:
        "up" or "down".
    """
    if not django.conf.settings.DATACITE_ENABLED:
        return "up"
    # To hide transient network errors, we make multiple attempts.
    for i in range(django.conf.settings.DATACITE_NUM_ATTEMPTS):
        o = urllib.request.build_opener(_HTTPErrorProcessor)
        r = urllib.request.Request(
            django.conf.settings.DATACITE_DOI_URL + "/" + django.conf.settings.DATACITE_PING_DOI
        )
        # We manually supply the HTTP Basic authorization header to avoid
        # the doubling of the number of HTTP transactions caused by the
        # challenge/response model.
        r.add_header(
            "Authorization",
            _authorization(
                django.conf.settings.DATACITE_PING_DOI,
                django.conf.settings.DATACITE_PING_DATACENTER,
            ),
        )
        c = None
        try:
            c = o.open(r, timeout=django.conf.settings.DATACITE_TIMEOUT)
            assert c.read() == django.conf.settings.DATACITE_PING_TARGET
        except Exception:
            if i == django.conf.settings.DATACITE_NUM_ATTEMPTS - 1:
                return "down"
        else:
            return "up"
        finally:
            if c:
                c.close()
        # increase reattempt delay as a magnitude of DATACITE_NUM_ATTEMPTS
        time.sleep(django.conf.settings.DATACITE_REATTEMPT_DELAY + (60 * (i + 1)))


def dcmsRecordToHtml(record):
    """Convert a DataCite Metadata Scheme <http://schema.datacite.org/> record
    to an XHTML table

    Args:
        record: The record should be unencoded.

    Returns:
        XHTML table or None on error.
    """
    try:
        r = lxml.etree.tostring(
            lxml.etree.XSLT(
                lxml.etree.parse(
                    os.path.join(django.conf.settings.PROJECT_ROOT, "profiles", "datacite.xsl")
                )
            )(impl.util.parseXmlString(record)),
            encoding=str,
        )
        assert r.startswith("<table")
        return r
    except Exception:
        return None

def removeXMLNamespacePrefix(record):
    """Remove namespace prefixes from XML elements andd attributes.

    Args:
        record: The record should be unencoded.

    Returns:
        XML record or None on error.
    """
    try:
        r = lxml.etree.tostring(
            lxml.etree.XSLT(
                lxml.etree.parse(
                    os.path.join(django.conf.settings.PROJECT_ROOT, "profiles", "remove_ns_prefix.xsl")
                )
            )(impl.util.parseXmlString(record)),
            encoding=str,
        )
        return r
    except Exception:
        return None
    
def dcmsRecordToDict(record):
    """Convert a DataCite Metadata Scheme <http://schema.datacite.org/> record
    to a dict.

    Args:
        record: The record should be unencoded.

    Returns:
        A dict or None on error.
    """
    record_dict = xmltodict.parse(str(record))
    return record_dict

def briefDataciteRecord(record):
    """Convert a DataCite Metadata Scheme <http://schema.datacite.org/> record
    to a dictionary in simple DataCite format with data fields for Citation Preview.

    Args:
        record: Datacite record in XML.

    Returns:
        A dict or None on error. The dict contains the following keys:
        - 'datacite.creator'
        - 'datacite.title'
        - 'datacite.publisher'
        - 'datacite.publicationyear'
        - 'datacite.resourcetype'
    """

    datacite_dict = dcmsRecordToDict(record)
    briefDcRecord = {}
    try:
        if datacite_dict and 'resource' in datacite_dict:
            if 'creators' in datacite_dict['resource'] and 'creator' in datacite_dict['resource']['creators']:
                creator = datacite_dict['resource']['creators']['creator']
                if isinstance(creator, list):
                    et_al = ''
                    for i in range(len(creator)):
                        if 'creatorName' in creator[i]:
                            if 'datacite.creator' not in briefDcRecord:
                                briefDcRecord['datacite.creator'] = get_dict_value_by_key(creator[i]['creatorName'], '#text')
                            else:
                                et_al = 'et al.'
                    if briefDcRecord['datacite.creator'] and et_al != '':
                        briefDcRecord['datacite.creator'] += f' {et_al}'
                else:
                    if 'creatorName' in creator:
                        briefDcRecord['datacite.creator'] = get_dict_value_by_key(creator['creatorName'], '#text')
                        
            if 'titles' in datacite_dict['resource'] and 'title' in datacite_dict['resource']['titles']:
                title = datacite_dict['resource']['titles']['title']
                if isinstance(title, list):
                    if len(title) > 0:
                        briefDcRecord['datacite.title'] = get_dict_value_by_key(title[0], '#text')
                else:
                    briefDcRecord['datacite.title'] = get_dict_value_by_key(title, '#text')

            if 'publisher' in datacite_dict['resource']:
                briefDcRecord['datacite.publisher'] = get_dict_value_by_key(datacite_dict['resource']['publisher'], '#text')
            
            if 'publicationYear' in datacite_dict['resource']:
                briefDcRecord['datacite.publicationyear'] = datacite_dict['resource']['publicationYear']
            
            if 'resourceType' in datacite_dict['resource']:
                briefDcRecord['datacite.resourcetype'] = get_dict_value_by_key(datacite_dict['resource']['resourceType'], '@resourceTypeGeneral')
    except Exception as ex:
        log.error(f'error: {ex} - brief record: {briefDcRecord}')
        
    return briefDcRecord

def get_dict_value_by_key(input_dict, key):
    if isinstance(input_dict, dict) and key in input_dict:
        return input_dict.get(key)
    else:
        return input_dict

def crossrefToDatacite(record, overrides=None):
    """Convert a Crossref Deposit Schema <http://help.crossref.org/deposit_schema>
    document to DataCite

    Args:
        record:
            Metadata Scheme <http://schema.datacite.org/> record.
        overrides:
            Dictionary of individual metadata element names (e.g., "datacite.title") and
            values that override the conversion values that would normally be drawn from
            the input document.

    Returns:
        Throws an exception on error.
    """
    overrides = overrides or {}
    d = {}
    for k, v in list(overrides.items()):
        # noinspection PyArgumentList
        d[k] = lxml.etree.XSLT.strparam(v)
    return lxml.etree.tostring(
        lxml.etree.XSLT(
            lxml.etree.parse(
                os.path.join(
                    django.conf.settings.PROJECT_ROOT,
                    "profiles",
                    "crossref2datacite.xsl",
                )
            )
        )(impl.util.parseXmlString(record), **d),
        encoding=str,
    )


def upgradeDcmsRecord(record, parseString=True, returnString=True):
    """Convert a DataCite Metadata Scheme <http://schema.datacite.org/> record to the
    latest version of the schema (currently, version 4)

    Note (2025-04-21): This function is deprecated when EZID withdraw support of old schema versions (2 & 3).
    It is kept for furture reference when supporting old schema version is needed.

    Args:
        record:
        parseString:
            The record must be supplied as an unencoded Unicode string if 'parseString'
            is true, or a root lxml.etree.Element object if not.
        returnString:
            If true, the record is returned as an unencoded Unicode string, in which
            case the record has no XML declaration. Otherwise, an lxml.etree.Element
            object is returned. In both cases, the root element's xsi:schemaLocation
            attribute is set or added as necessary.
    """
    if parseString:
        root = impl.util.parseXmlString(record)
    else:
        root = record
    root.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"] = (
        "http://datacite.org/schema/kernel-4 "
        + "http://schema.datacite.org/meta/kernel-4/metadata.xsd"
    )
    m = _SCHEMA_VERSION_RE.match(root.tag)
    if m.group(1) == "4":
        # Nothing to do.
        if returnString:
            return lxml.etree.tostring(root, encoding=str)
        else:
            return root

    def q(elementName):
        return "{http://datacite.org/schema/kernel-4}" + elementName

    def changeNamespace(node):
        if node.tag is not lxml.etree.Comment:
            # The order is important here: parent before children.
            node.tag = q(node.tag.split("}")[1])
            for child in node:
                changeNamespace(child)

    changeNamespace(root)
    ns = {"N": "http://datacite.org/schema/kernel-4"}
    # Resource type is required as of version 4.
    e = root.xpath("//N:resourceType", namespaces=ns)
    assert len(e) <= 1
    if len(e) == 1:
        if e[0].attrib["resourceTypeGeneral"] == "Film":
            e[0].attrib["resourceTypeGeneral"] = "Audiovisual"
    else:
        e = lxml.etree.SubElement(root, q("resourceType"))
        e.attrib["resourceTypeGeneral"] = "Other"
        e.text = "(:unav)"
    # There's no way to assign new types to start and end dates, so just
    # delete them.
    for e in root.xpath("//N:date", namespaces=ns):
        if e.attrib["dateType"] in ["StartDate", "EndDate"]:
            e.getparent().remove(e)
    for e in root.xpath("//N:dates", namespaces=ns):
        if len(e) == 0:
            e.getparent().remove(e)
    # The contributor type "Funder" went away in version 4.
    for e in root.xpath("//N:contributor[@contributorType='Funder']", namespaces=ns):
        fr = root.xpath("//N:fundingReferences", namespaces=ns)
        if len(fr) > 0:
            fr = fr[0]
        else:
            fr = lxml.etree.SubElement(root, q("fundingReferences"))
        for n in e.xpath("N:contributorName", namespaces=ns):
            lxml.etree.SubElement(
                lxml.etree.SubElement(fr, q("fundingReference")), q("funderName")
            ).text = n.text
        e.getparent().remove(e)
    for e in root.xpath("//N:contributors", namespaces=ns):
        if len(e) == 0:
            e.getparent().remove(e)
    # Geometry changes in version 4.
    for e in root.xpath("//N:geoLocationPoint", namespaces=ns):
        if len(e) == 0:
            coords = e.text.split()
            if len(coords) == 2:
                lxml.etree.SubElement(e, q("pointLongitude")).text = coords[1]
                lxml.etree.SubElement(e, q("pointLatitude")).text = coords[0]
                e.text = None
            else:
                # Should never happen.
                e.getparent().remove(e)
    for e in root.xpath("//N:geoLocationBox", namespaces=ns):
        if len(e) == 0:
            coords = e.text.split()
            if len(coords) == 4:
                lxml.etree.SubElement(e, q("westBoundLongitude")).text = coords[1]
                lxml.etree.SubElement(e, q("eastBoundLongitude")).text = coords[3]
                lxml.etree.SubElement(e, q("southBoundLatitude")).text = coords[0]
                lxml.etree.SubElement(e, q("northBoundLatitude")).text = coords[2]
                e.text = None
            else:
                # Should never happen.
                e.getparent().remove(e)
    lxml.etree.cleanup_namespaces(root)
    if returnString:
        return lxml.etree.tostring(root, encoding=str)
    else:
        return root

def upgradeDcmsRecord_v2(record, parseString=True, returnString=True):
    """Setup DataCite Metadata Scheme version 4 schemaLocation.
    Report error if schema versions is not supported by EZID.
    Note (2025-04-21): This function is derived from funciton 'upgradeDcmsRecord()' 
    when EZID withdraw support of old schema versions (2 & 3).

    Args:
        record:
        parseString:
            The record must be supplied as an unencoded Unicode string if 'parseString'
            is true, or a root lxml.etree.Element object if not.
        returnString:
            If true, the record is returned as an unencoded Unicode string, in which
            case the record has no XML declaration. Otherwise, an lxml.etree.Element
            object is returned. In both cases, the root element's xsi:schemaLocation
            attribute is set or added as necessary.
    """
    if parseString:
        root = impl.util.parseXmlString(record)
    else:
        root = record
    
    root.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"] = (
        "http://datacite.org/schema/kernel-4 "
        + "http://schema.datacite.org/meta/kernel-4/metadata.xsd"
    )

    m = _SCHEMA_VERSION_RE.match(root.tag)
    version = m.group(1)
    if version == "4":
        if returnString:
            return lxml.etree.tostring(root, encoding=str)
        else:
            return root
    else:
        assert False, "DataCite schema version {} is not supported".format(version)


def _deactivate(doi, datacenter):
    # To hide transient network errors, we make multiple attempts.
    for i in range(django.conf.settings.DATACITE_NUM_ATTEMPTS):
        o = urllib.request.build_opener(_HTTPErrorProcessor)
        r = urllib.request.Request(
            django.conf.settings.DATACITE_METADATA_URL + "/" + urllib.parse.quote(doi)
        )
        # We manually supply the HTTP Basic authorization header to avoid the doubling
        # of the number of HTTP transactions caused by the challenge/response model.
        r.add_header("Authorization", _authorization(doi, datacenter))
        r.get_method = lambda: "DELETE"
        c = None
        try:
            c = o.open(r, timeout=django.conf.settings.DATACITE_TIMEOUT)
            assert c.read() == "OK", "Unexpected return from DataCite deactivate DOI operation"
        except urllib.error.HTTPError as e:
            if e.code != 500 or i == django.conf.settings.DATACITE_NUM_ATTEMPTS - 1:
                raise e
        except Exception:
            if i == django.conf.settings.DATACITE_NUM_ATTEMPTS - 1:
                raise
        else:
            break
        finally:
            if c:
                c.close()
        # increase reattempt delay as a magnitude of DATACITE_NUM_ATTEMPTS
        time.sleep(django.conf.settings.DATACITE_REATTEMPT_DELAY + (60 * (i + 1)))


def _authorization(doi, datacenter=None):
    if datacenter is None:
        s = ezidapp.models.shoulder.getLongestShoulderMatch("doi:" + doi)
        # Should never happen.
        assert s is not None, "Shoulder not found"
        datacenter = s.datacenter.symbol
    a = datacenter.split(".")[0]
    p = ALLOCATOR_DICT.get(a, None)
    assert p is not None, "No such allocator: " + a
    return impl.util.basic_auth(datacenter, p)
