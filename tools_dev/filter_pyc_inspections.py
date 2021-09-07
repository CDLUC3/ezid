#!/usr/bin/env python

"""Filter inspections exported from PyCharm

This can be used to pick out inspection issues that match some pattern and process them
as a batch.

Usage:
    - Run inspections in PyCharm
    - In the Inspection Results, Export > Export to XML
    - Only the output dir is selectable, not the the filename. That's because
    PyCharm uses the filename to recognize the type of XML file.
    - Add code in this script to filter the inspections
    - Import the file in PyCharm with 'View Offline Inspection Results'. (The title is
    misleading -- after import, the XML doc shows up as a regular inspection result with
    full functionality)
"""

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import logging
import pathlib
import re
import sys

import lxml.etree

log = logging.getLogger(__name__)

# PyCharm stores type of inspection in the filename, so we can only control the
# location, not the name of this file.
inspection_name = 'PyUnresolvedReferencesInspection.xml'

filter1_rx = re.compile("^Cannot find reference.*in 'None'")
filter_rx = re.compile("'next'")


def main():
    xml_str = pathlib.Path(inspection_name).read_text()
    root_el = lxml.etree.XML(xml_str)
    out_el = lxml.etree.Element('problems')

    for el in root_el.findall('.//problem'):

        desc_str = el.find('description').text

        if filter_rx.search(desc_str):
            print(desc_str)
            out_el.append(el)

    pathlib.Path('out', inspection_name).write_bytes(
        lxml.etree.tostring(out_el, pretty_print=True)
    )


if __name__ == '__main__':
    sys.exit(main())
