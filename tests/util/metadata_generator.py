#!/usr/bin/env python

"""Generate Crossref, DataCite and DC metadata test objects.

The objects are based on samples from the EZID production database. The text nodes have
been modified to indicate that they are generic test objects.

The XML data is modified for each metadata object in which they are used, then combined
with key/value pairs require by the EZID API, then formatted to ANVL.
"""
import logging

import lxml
import lxml.etree

log = logging.getLogger(__name__)


def get_metadata(id_ns, test_docs, meta_type=None):
    """Return metadata in an interleaved list, ready to be passed to the ANVL formatter.
    meta_type must be 'datacite' or 'crossref'.
    """
    if meta_type is None:
        return _get_dc_metadata(id_ns)
    return _get_metadata_with_xml(id_ns, test_docs, meta_type)


def _get_metadata_with_xml(id_ns, test_docs, meta_type):
    meta_dict = _TYPE_DICT[meta_type]
    root_el = _parse_xml((test_docs / meta_dict['xml']).read_text())
    anvl_dict = meta_dict['anvl'].copy()
    meta_dict['set_id'](root_el, id_ns)
    xml_str = _to_compact_string(root_el)
    anvl_dict[meta_type] = xml_str
    return _to_interleaved_list(anvl_dict)


def _get_dc_metadata(id_ns):
    return _to_interleaved_list(
        {
            'dc.creator': 'Test creator for DC metadata record',
            'dc.date': '1999-01-02',
            'dc.extent': '1 pages',
            'dc.identifier': str(id_ns),
            'dc.title': 'Test title for DC metadata record',
        }
    )


NAMESPACE_DICT = {
    'datacite': 'http://datacite.org/schema/kernel-3',
    'crossref': 'http://www.crossref.org/schema/4.4.0',
}

_CROSSREF_METADATA_DICT = {
    'crossref': None,
}

_DATACITE_METADATA_DICT = {
    'datacite': None,
    'datacite.creator': 'Last, First',
    'datacite.format': 'text/plain',
    'datacite.publicationyear': '1999',
    'datacite.publisher': 'Test publisher',
    'datacite.resourcetype': 'Dataset / data',
    'datacite.size': '1234567',
    'datacite.title': '(:unkn)',
}


def _set_datacite_identifier(root_el, id_ns):
    # id_type: /resource/identifier/@identifierType
    # id_value: /resource/identifier/text()
    el = root_el.xpath(
        './/datacite:identifier',
        # './/datacite:identifier/@identifierType',
        namespaces=NAMESPACE_DICT,
    )[0]
    el.attrib['identifierType'] = id_ns.scheme.upper()
    el.text = str(id_ns)


def _set_crossref_identifier(root_el, id_ns):
    # id_type: Always DOI
    # id_value: /database/doi_data/doi/text()
    log.debug(_to_pretty_string(root_el))
    el = root_el.xpath('.//crossref:doi_data/crossref:doi', namespaces=NAMESPACE_DICT)[
        0
    ]
    el.text = str(id_ns)


_TYPE_DICT = {
    'datacite': {
        'xml': 'datacite_metadata.xml',
        'anvl': _DATACITE_METADATA_DICT,
        'set_id': _set_datacite_identifier,
    },
    'crossref': {
        'xml': 'crossref_metadata.xml',
        'anvl': _CROSSREF_METADATA_DICT,
        'set_id': _set_crossref_identifier,
    },
}


def _mk_crossref_metadata_list(meta_dict, meta_xml, id_ns):
    root_el = _parse_xml(meta_xml)
    _set_crossref_identifier(root_el, id_ns)
    xml_str = _to_compact_string(root_el)
    meta_dict['crossref'] = xml_str
    return _to_interleaved_list(meta_dict)


def _to_compact_string(root_el):
    """Render an lxml etree to a string that does not have any whitespace between the elements.
    - Requires that the parser already has removed non-significant whitespace between
    elements.
    - Whitespace is deemed to be non-significant only when there is no text between the
    elements.
    - Reformatting XML often causes whitespace to be added, which can't be automatically
    be removed later (because, without a schema, there's no way for a parser or
    formatter to know if the whitespace is significant.
    """
    return lxml.etree.tostring(root_el, encoding=str, pretty_print=False)
    # with io.BytesIO() as ss:
    #     lxml.etree.ElementTree(root_el).write(ss)
    #     return ss.getvalue()


def _to_pretty_string(root_el):
    """Render an lxml etree to a string that does not have any whitespace between elements"""
    return lxml.etree.tostring(root_el, encoding=str, pretty_print=True)


def _to_interleaved_list(meta_dict):
    """Convert a metadata dict (key/value) to the flat interleaved list format required
    by our ANVL formatter."""
    return tuple(s.strip() for kv in meta_dict.items() for s in kv)


def _parse_xml(xml_str):
    parser = lxml.etree.XMLParser(remove_blank_text=True)
    root_el = lxml.etree.XML(xml_str, parser=parser)
    return root_el


# if __name__ == '__main__':
#     logging.basicConfig(
#         level=logging.DEBUG,
#         format='%(levelname)-8s %(message)s',
#         stream=sys.stderr,
#     )
#
#     ns = impl.nog.id_ns.IdNamespace.from_str('ark:/12343/k3')
#     meta_list = get_metadata(test_docs, ns, 'crossref')
#     print(meta_list)
