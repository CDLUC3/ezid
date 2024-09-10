#!/usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Create Django settings module for unit tests from Jinja template file and constants.

Current paths are:

Settings dir path: ezid/settings
Settings template path: ezid/settings/settings.py.j2
Settings module path: ezid/settings/tests.py

The constants are stored directly in this file.
"""

import pathlib
import sys

import jinja2

TEMPLATE_VARS = {
    'ezid_base_url': 'http://localhost:8000',
    'ezid_version': 'TEST_INSTANCE',
    # DB
    'database_host': 'localhost',
    'database_name': 'ezid_test_db',
    'database_user': 'ezid_test_user',
    'database_password': 'ezid_test_pw',
    'database_port': '3306',
    # Admin
    'email_new_account': 'invalid@invalid.invalid',
    'admin_username': 'admin',
    'admin_password': 'admin',
    'admin_groupname': 'admin',
    'admin_notes': '',
    'admin_email': 'ezid@ucop.edu',
    'admin_display_name': 'EZID superuser',
    'admin_org_acronym': 'CDL',
    'admin_org_name': 'EZID',
    'admin_org_url': 'http://ezid.cdlib.org/',
    'admin_crossref_email': '',
    'admin_crossref_enabled': False,
    'admin_primary_contact_email': 'ezid@ucop.edu',
    'admin_primary_contact_name': 'EZID superuser',
    'admin_primary_contact_phone': '',
    'admin_secondary_contact_email': '',
    'admin_secondary_contact_name': '',
    'admin_secondary_contact_phone': '',
    'admin_search_realm': 'CDL',
    'admin_search_user_pid': 'ark:/99166/p9kw57h4w',
    'admin_search_group_pid': 'ark:/99166/p9g44hq02',
    # Misc
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
    print('Generating test settings')
    settings_path = pathlib.Path(__file__).resolve().parents[2] / 'settings'
    template_path = settings_path / 'settings.py.j2'
    tests_path = settings_path / 'tests.py'
    print(f'Settings dir path: {settings_path.as_posix()}')
    print(f'Settings template path: {template_path.as_posix()}')
    print(f'Settings module path: {tests_path.as_posix()}')
    template_str = template_path.read_text()
    tests_path.write_text(jinja2.Template(template_str).render(TEMPLATE_VARS))


if __name__ == '__main__':
    sys.exit(main())
