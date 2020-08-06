import bz2
import io
import logging

import django
import pytest
import utils.filesystem

from django.core.management import call_command

DEFAULT_DB_KEY = 'default'
REL_DB_FIXTURE_PATH = '../ezidapp/fixtures/store-full-pp.json'


log = logging.getLogger(__name__)


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Populate the database from a fixture"""
    with django_db_blocker.unblock():
        # django_load_db_fixture(REL_DB_FIXTURE_PATH)
        fixture_file_path = utils.filesystem.abs_path(REL_DB_FIXTURE_PATH)
        call_command(
            'loaddata',
            fixture_file_path,
            exclude=[
                # 'admin',
                # 'auth',
                'contenttypes',
                # 'messages',
                # 'sessions',
                # 'ui_tags',
                # 'ezidapp',
            ],
        )


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Make the Django DB available to all tests. This will use Django's default DB,
    which is the "store" DB in EZID. The DB connection is set up according to the
    DJANGO_SETTINGS_MODULE setting in ezid/tox.ini.
    """
    pass


@pytest.fixture()
def tmp_bdb_root(mocker, tmp_path):
    """Temporary root for BerkeleyDB minters"""
    minters_path = tmp_path / 'minters'
    mocker.patch(
        'nog_minter.get_bdb_root', return_value=minters_path.resolve().as_posix()
    )


def django_save_db_fixture(db_key=DEFAULT_DB_KEY):
    """Save database to a bz2 compressed JSON fixture"""
    fixture_file_path = utils.filesystem.abs_path(REL_DB_FIXTURE_PATH)
    logging.info('Writing fixture. path="{}"'.format(fixture_file_path))
    buf = io.StringIO()
    django.core.management.call_command(
        "dumpdata",
        exclude=["auth.permission", "contenttypes"],
        database=db_key,
        stdout=buf,
    )
    with bz2.BZ2File(
        fixture_file_path, "w", buffering=1024 ** 2, compresslevel=9
    ) as bz2_file:
        bz2_file.write(buf.getvalue().encode("utf-8"))
