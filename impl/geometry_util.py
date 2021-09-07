#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Geometry-related utility functions
"""

import json
import re

import lxml.etree

import impl.util

# N.B.: the namespace for KML 2.3 is still 2.2.
_kmlNamespace = "http://www.opengis.net/kml/2.2"
_dataciteNamespace = "http://datacite.org/schema/kernel-4"


def _q(elementName):
    return f"{{{_dataciteNamespace}}}{elementName}"


def _isDecimalFloat(s):
    return re.match("-?(\\d+(\\.\\d*)?|\\.\\d+)$", s) is not None


def kmlPolygonToDatacite(kml):
    """Convert a polygon defined in a KML

    <http://www.opengeospatial.org/standards/kml> version 2.2 or 2.3
    document to a DataCite 4.0 <geoLocationPolygon> element.  The return
    is a pair (lxml.etree.Element, [warning, ...]) if successful or a
    string error message if not.  The conversion fails for the usual
    reasons (malformed KML, etc.) but also if the document defines more
    than one geometry or does not define a polygon.  Polygon holes and
    non-zero altitude coordinates are ignored and result in warnings.
    """
    try:
        root = impl.util.parseXmlString(kml)
    except Exception as e:
        return "XML parse error: " + impl.util.formatException(e)
    if root.tag != f"{{{_kmlNamespace}}}kml":
        return "not a KML document"
    ns = {"N": _kmlNamespace}
    n = root.xpath("//N:Polygon", namespaces=ns)
    if len(n) == 0:
        return "no polygon found"
    if (
        len(n) > 1
        or len(root.xpath("//N:Point", namespaces=ns)) > 0
        or len(root.xpath("//N:LineString", namespaces=ns)) > 0
        or len(root.xpath("//N:Model", namespaces=ns)) > 0
        or len(root.xpath("//N:Track", namespaces=ns)) > 0
    ):
        return "document defines more than one geometry"
    innerBoundaryWarning = len(n[0].xpath("N:innerBoundaryIs", namespaces=ns)) > 0
    n = n[0].xpath("N:outerBoundaryIs", namespaces=ns)
    if len(n) != 1:
        return "polygon contains zero or multiple outer boundaries"
    n = n[0].xpath("N:LinearRing", namespaces=ns)
    if len(n) != 1:
        return "polygon outer boundary contains zero or multiple linear rings"
    n = n[0].xpath("N:coordinates", namespaces=ns)
    if len(n) != 1:
        return (
            "polygon outer boundary contains zero or multiple " + "coordinates elements"
        )
    output = lxml.etree.Element(
        _q("geoLocationPolygon"), nsmap={None: _dataciteNamespace}
    )
    altitudeWarning = False
    for ct in n[0].text.split():
        c = ct.split(",")
        if (
            len(c) not in [2, 3]
            or not _isDecimalFloat(c[0])
            or not _isDecimalFloat(c[1])
            or (len(c) == 3 and not _isDecimalFloat(c[2]))
        ):
            return "malformed coordinates"
        if (
            float(c[0]) < -180
            or float(c[0]) > 180
            or float(c[1]) < -90
            or float(c[1]) > 90
        ):
            return "coordinates out of range"
        p = lxml.etree.SubElement(output, _q("polygonPoint"))
        lxml.etree.SubElement(p, _q("pointLongitude")).text = c[0]
        lxml.etree.SubElement(p, _q("pointLatitude")).text = c[1]
        if len(c) == 3 and float(c[2]) != 0:
            altitudeWarning = True
    if len(output) < 4:
        return "polygon has insufficient coordinate tuples (4 required)"
    if float(output[0][0].text) != float(output[-1][0].text) or float(
        output[0][1].text
    ) != float(output[-1][1].text):
        return "polygon first coordinate does not match last"
    warnings = []
    if innerBoundaryWarning:
        warnings.append("polygon inner boundaries ignored")
    if altitudeWarning:
        warnings.append("altitude coordinates ignored")
    return output, warnings


_geojsonTypes = [
    "Point",
    "MultiPoint",
    "LineString",
    "MultiLineString",
    "Polygon",
    "MultiPolygon",
    "GeometryCollection",
]


def _isNestedList(o, n):
    if type(o) is not list:
        return False
    if n > 1:
        if len(o) == 0:
            return False
        if not all(_isNestedList(m, n - 1) for m in o):
            return False
    return True


def geojsonPolygonToDatacite(geojson):
    """Convert a polygon defined in a GeoJSON <RFC 7946,
    https://tools.ietf.org/html/rfc7946> document to a DataCite 4.0.

    <geoLocationPolygon> element.  The return is a pair
    (lxml.etree.Element, [warning, ...]) if successful or a string error
    message if not.  The conversion fails for the usual reasons
    (malformed JSON, etc.) but also if the document defines more than
    one geometry or does not define a polygon.  Polygon holes and non-
    zero altitude coordinates are ignored and result in warnings.
    """
    objects = []

    def objectHandler(d):
        if (
            d.get("type", "unknown") in _geojsonTypes
            and d["type"] != "GeometryCollection"
        ):
            objects.append(d)
        return d

    try:
        root = json.loads(geojson, object_hook=objectHandler)
    except Exception as e:
        return "JSON parse error: " + impl.util.formatException(e)
    if type(root) is not dict or root.get("type", "unknown") not in _geojsonTypes:
        return "not a GeoJSON document"
    if len(objects) > 1:
        return "document defines more than one geometry"
    if len(objects) == 0 or objects[0]["type"] not in ["Polygon", "MultiPolygon"]:
        return "no polygon found"
    p = objects[0]
    if not _isNestedList(p.get("coordinates", {}), 3 if p["type"] == "Polygon" else 4):
        return "malformed GeoJSON document"
    if p["type"] == "MultiPolygon":
        if len(p["coordinates"]) > 1:
            return "document defines more than one geometry"
        p["coordinates"] = p["coordinates"][0]
    innerBoundaryWarning = len(p["coordinates"]) > 1
    output = lxml.etree.Element(
        _q("geoLocationPolygon"), nsmap={None: _dataciteNamespace}
    )
    altitudeWarning = False
    for ct in p["coordinates"][0]:
        if (
            len(ct) not in [2, 3]
            or not isinstance(ct[0], (int, float))
            or not isinstance(ct[1], (int, float))
            or (len(ct) == 3 and not isinstance(ct[2], (int, float)))
        ):
            return "malformed coordinates"
        if (
            float(ct[0]) < -180
            or float(ct[0]) > 180
            or float(ct[1]) < -90
            or float(ct[1]) > 90
        ):
            return "coordinates out of range"
        p = lxml.etree.SubElement(output, _q("polygonPoint"))
        lxml.etree.SubElement(p, _q("pointLongitude")).text = str(ct[0])
        lxml.etree.SubElement(p, _q("pointLatitude")).text = str(ct[1])
        if len(ct) == 3 and float(ct[2]) != 0:
            altitudeWarning = True
    if len(output) < 4:
        return "polygon has insufficient coordinate tuples (4 required)"
    if float(output[0][0].text) != float(output[-1][0].text) or float(
        output[0][1].text
    ) != float(output[-1][1].text):
        return "polygon first coordinate does not match last"
    warnings = []
    if innerBoundaryWarning:
        warnings.append("polygon inner boundaries ignored")
    if altitudeWarning:
        warnings.append("altitude coordinates ignored")
    return output, warnings


def internalPolygonToDatacite(s):
    """Convert an internal polygon description to a DataCite 4.0

    <geoLocationPolygon> element.  An internal description is a string
    of the form

       polygon ((lon, lat), (lon, lat), ...)

    For conformity with other conversion functions in this module, the
    return is a pair (lxml.etree.Element, []) if successful or a string
    error message if not.
    """
    m = re.match("\\s*polygon\\s*\\((.*)\\)\\s*$", s)
    if not m:
        return "not an EZID polygon description"
    coords = re.split("\\s*\\)\\s*,\\s*\\(\\s*", f"),{m.group(1)},(")
    if (
        len(coords) < 2
        or coords[0] != ""
        or coords[-1] != ""
        or any(ct == "" for ct in coords[1:-1])
    ):
        return "malformed polygon description"
    if len(coords) < 1 + 4 + 1:
        return "polygon has insufficient coordinate tuples (4 required)"
    output = lxml.etree.Element(
        _q("geoLocationPolygon"), nsmap={None: _dataciteNamespace}
    )
    for ct in coords[1:-1]:
        ct = [c.strip() for c in ct.split(",")]
        if len(ct) != 2 or not _isDecimalFloat(ct[0]) or not _isDecimalFloat(ct[1]):
            return "malformed polygon description"
        if (
            float(ct[0]) < -180
            or float(ct[0]) > 180
            or float(ct[1]) < -90
            or float(ct[1]) > 90
        ):
            return "coordinates out of range"
        p = lxml.etree.SubElement(output, _q("polygonPoint"))
        lxml.etree.SubElement(p, _q("pointLongitude")).text = ct[0]
        lxml.etree.SubElement(p, _q("pointLatitude")).text = ct[1]
    if float(output[0][0].text) != float(output[-1][0].text) or float(
        output[0][1].text
    ) != float(output[-1][1].text):
        return "polygon first coordinate does not match last"
    return output, []


def polygonToDatacite(s):
    """Convert a polygon defined in any supported format to a DataCite 4.0

    <geoLocationPolygon> element.  The return is a pair
    (lxml.etree.Element, [warning, ...]) if successful or a string error
    message if not.
    """
    if "kml" in s:
        r = kmlPolygonToDatacite(s)
        if type(r) is str:
            return "KML conversion failed: " + r
        else:
            return r
    elif s.strip().startswith("{") and "type" in s:
        r = geojsonPolygonToDatacite(s)
        if type(r) is str:
            return "GeoJSON conversion failed: " + r
        else:
            return r
    elif "polygon" in s:
        r = internalPolygonToDatacite(s)
        if type(r) is str:
            return "polygon conversion failed: " + r
        else:
            return r
    else:
        return "unrecognized polygon format"


_transform = None
_transformSource = """<?xml version="1.0"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
<xsl:output method="text"/>
<xsl:template match="*[local-name()='geoLocationPolygon']">
  <xsl:text>polygon (</xsl:text>
  <xsl:apply-templates select="*[local-name()='polygonPoint']"/>
  <xsl:text>)</xsl:text>
</xsl:template>
<xsl:template match="*[local-name()='polygonPoint']">
  <xsl:if test="position() != 1">
    <xsl:text>, </xsl:text>
  </xsl:if>
  <xsl:text>(</xsl:text>
  <xsl:value-of select="*[local-name()='pointLongitude']"/>
  <xsl:text>,</xsl:text>
  <xsl:value-of select="*[local-name()='pointLatitude']"/>
  <xsl:text>)</xsl:text>
</xsl:template>
</xsl:stylesheet>"""


def datacitePolygonToInternal(element):
    """Convert a DataCite polygon, passed in as a <geoLocationPolygon> element
    node, to a string internal representation."""
    global _transform
    if _transform is None:
        _transform = lxml.etree.XSLT(lxml.etree.XML(_transformSource))
    return str(_transform(element))
