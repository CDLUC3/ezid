#!/usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Create test_settings.py from settings_template.py

Run with CWD in root of a EZID worktree.
"""

import pathlib
import sys

import jinja2

TEMPLATE_VARS = {
    'ezid_base_url': 'https://ezid.cdlib.org',
    'database_host': 'localhost',
    'database_name': 'ezid_test_db',
    'database_user': 'ezid_test_user',
    'database_password': '',
    'database_port': '3306',
    'email_new_account': 'invalid@invalid.invalid',
    'admin_username': 'admin',
    'admin_password': 'admin',
    'resolver_doi': 'https://doi.org',
    'resolver_ark': 'https://n2t-stg.n2t.net',
    'datacite_doi_url': 'https://mds.datacite.org/doi',
    'datacite_metadata_url': 'https://mds.datacite.org/metadata',
    'allocator_cdl_password': '',
    'allocator_purdue_password': '',
    'crossref_username': '',
    'crossref_password': '',
    'cloudwatch_instance_name': 'uc3-ezidx2-dev',
}


def main():
    print('Creating settings.tests')
    settings_path = pathlib.Path(__file__).resolve().parents[2] / 'settings'
    template_str = (settings_path / 'settings_template.py').read_text()
    test_settings_path = settings_path / 'test_settings.py'
    test_settings_path.write_text(jinja2.Template(template_str).render(TEMPLATE_VARS))


if __name__ == '__main__':
    sys.exit(main())
