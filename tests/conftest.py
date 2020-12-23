import bz2
import csv
import io
import logging
import os
import sys

import django
import django.conf
import django.contrib.auth.models
import django.contrib.sessions.models
import django.core.management
import django.db
import django.db.transaction
import django.http.request
import pathlib2
import pytest

import config
import ezidapp
import ezidapp.models
import nog.filesystem
import nog.shoulder
import tests.util.sample
import tests.util.util

DEFAULT_DB_KEY = 'default'
import nog.id_ns

NAMESPACE_LIST = [
    (nog.id_ns.IdNamespace.from_str('ark:/99933/x1'), tuple()),
    (nog.id_ns.IdNamespace.from_str('ark:/99934/x2'), tuple()),
    (nog.id_ns.IdNamespace.from_str('ark:/99933/x3y4'), ('supershoulder',)),
    (nog.id_ns.IdNamespace.from_str('ark:/99934/'), ('supershoulder', 'force',)),
    (nog.id_ns.IdNamespace.from_str('doi:10.9935/X5'), ('datacenter',)),
    (nog.id_ns.IdNamespace.from_str('doi:10.19936/X6Y7'), ('datacenter',)),
    (nog.id_ns.IdNamespace.from_str('doi:10.9935/X8'), ('crossref',)),
    (nog.id_ns.IdNamespace.from_str('doi:10.19936/X9Y0'), ('crossref',)),
]

SHOULDER_CSV = nog.filesystem.abs_path('./test_docs/ezidapp_shoulder.csv')

# Database fixtures

# combined-limited: Complete snapshot of the combined store/search DB from stg. All tables
# are included but limited to 1000 rows.
REL_DB_FIXTURE_PATH = '../ezidapp/fixtures/combined-limited.json'

# store-full: Complete snapshot of the combined store/search DB from stg, only the three
# large tables holding the resolve metadata for the existing minters have been dropped.
# It's pretty slow to load as a fixture, so not used by default.
# REL_DB_FIXTURE_PATH = '../ezidapp/fixtures/store-full-pp.json'

# store-test: Small DB with only a few shoulder records. Fast to load as a fixture.
# REL_DB_FIXTURE_PATH = '../ezidapp/fixtures/store-test.json'


log = logging.getLogger(__name__)


# Hooks


def pytest_addoption(parser):
    parser.addoption(
        '--sample-error',
        action='store_true',
        default=False,
        help='Handle sample mismatch as test failure instead of opening diff viewer',
    )


def pytest_configure(config):
    """Allow plugins and conftest files to perform initial configuration.

    This hook is called for every plugin and initial conftest file after command line
    options have been parsed.

    After that, the hook is called for other conftest files as they are imported.
    """
    sys.is_running_under_travis = "TRAVIS" in os.environ
    sys.is_running_under_pytest = True

    tests.util.sample.options = {
        "error": config.getoption("--sample-error"),
    }

    # Only accept error messages from loggers that are noisy at debug.
    logging.getLogger('django.db.backends.schema').setLevel(logging.ERROR)


# Autouse fixtures


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Make the Django DB available to all tests.

    This will use Django's default DB, which is the "store" DB in EZID.
    The DB connection is set up according to the DJANGO_SETTINGS_MODULE
    setting in ezid/tox.ini.
    """
    pass


@pytest.fixture(scope='session')
def django_db_setup(django_db_keepdb):
    """Prevent pytest from clearing the database at the end of the test
    session. Also see the --reuse-db and --create-db pytest command line
    arguments.

    This also prevents Django from creating blank test databases, instead redirecting
    back to the main database.

    The tests are intended to run with real data in the database since that may help
    catch database related errors and provides context that the tests can reference
    without having to create it first.

    The database is populated from a fixture with a `./manage.py loaddata` command as
    required. On Travis, this is done in `./.travis.yml`.

    Changes made to the database by the tests are done in transactions that are rolled
    back after each test. However, tests done manually in the UI will permanently change
    the database, which may cause the tests to fail until the database is reset with
    `./manage.py loaddata`.

    Note: The name of this fixture must be 'django_db_setup', as it replaces the fixture
    of the same name in pytest-django.
    """
    django.conf.settings.DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "HOST": "localhost",
            "NAME": "ezid_tests",
            "USER": "travis",
            "PASSWORD": "",
            "OPTIONS": {"charset": "utf8mb4"},
            'DATABASE_OPTIONS': {'unix_socket': '/tmp/mysql.sock',},
        },
        "search": {
            "ENGINE": "django.db.backends.mysql",
            "HOST": "localhost",
            "NAME": "ezid_tests",
            "USER": "travis",
            "PASSWORD": "",
            "fulltextSearchSupported": True,
            "OPTIONS": {"charset": "utf8mb4"},
            'DATABASE_OPTIONS': {'unix_socket': '/tmp/mysql.sock',},
        },
    }


@pytest.fixture(autouse=True)
def disable_log_to_console(mocker):
    """Prevent management commands from reconfiguring the logging that has been
    set up by pytest."""
    mocker.patch('nog.util.log_to_console')


# Fixtures

# See also: https://pytest-django.readthedocs.io/en/latest/helpers.html#fixtures


@pytest.fixture(scope='function')
def reloaded():
    """Refresh EZID's in-memory caches of the database.

    In the test, additional reloads can be triggered by calling the
    fixture.
    """

    def reload_():
        assert django.conf.settings.configured
        config.reload()
        # noinspection PyProtectedMember
        log.debug(
            'reloaded(): db_shoulders={} cache_shoulders={}'.format(
                ezidapp.models.Shoulder.objects.filter(
                    active=True, manager='ezid'
                ).count(),
                len(ezidapp.models.shoulder._shoulders),
            )
        )

    reload_()
    return reload_


@pytest.fixture(scope='function')
def admin_admin(reloaded):
    """Set the admin password to "admin".

    This may be useful when testing authentication. To instead skip
    authentication, see skip_auth.
    """
    with django.db.transaction.atomic():
        if not django.contrib.auth.models.User.objects.filter(
            username='admin'
        ).exists():
            django.contrib.auth.models.User.objects.create_superuser(
                username='admin', password=None, email=""
            )
        reloaded()
        o = ezidapp.models.getUserByUsername('admin')
        o.setPassword('admin')
        o.save()
        reloaded()


@pytest.fixture(scope='function')
def skip_auth(django_db_keepdb, admin_client, mocker):
    """Replace EZID's user authentication system with a stub that successfully
    authenticates any user.

    The user must already exist in EZID. By default, only the admin user
    exists.
    """

    def mock_authenticate_request(request):
        user_id = get_user_id_by_session_key(request.session.session_key)
        return ezidapp.models.getUserById(user_id)

    mocker.patch('userauth.authenticateRequest', side_effect=mock_authenticate_request)


@pytest.fixture(scope='function')
def ez_admin(admin_client, admin_admin, skip_auth):
    """A Django test client that has been logged in as admin. When EZID
    endpoints are called via the client, a cookie for an active authenticated
    session is included automatically. This also sets the admin password to
    "admin".

    Note: Because EZID does not use a standard authentication procedure, it's also
    necessary to pull in skip_auth here.
    """
    admin_client.login(username='admin', password='admin')
    #log.info('cookies={}'.format(admin_client.cookies))
    return admin_client


@pytest.fixture(scope='function')
def ez_user(client, django_user_model):
    """A Django test client that has been logged in as a regular user named
    "ezuser", with password "password"."""
    username, password = "ezuser", "password"
    django_user_model.objects.create_user(username=username, password=password)
    client.login(username=username, password=password)
    return client


@pytest.fixture()
def tmp_bdb_root(mocker, tmp_path):
    """Set a temporary root directory for the BerkeleyDB minter hierarchy.

    By default, a BDB path resolved by the minter will reference a location in EZID's
    minter hierarchy, as configured in the EZID settings. Currently, `ezid/db/minters`.
    This fixture causes BDB paths to resolve to an empty tree under /tmp. Any minters
    created by the test are deleted when the test exits.

    Returns a pathlib2.Path referencing the root of the tree. The slash operator can be
    used for creating paths below the root. E.g., `tmp_bdb_root / 'b2345' / 'x1'`.
    """
    for dot_path in ('nog.bdb._get_bdb_root','impl.nog.bdb._get_bdb_root',):
        mocker.patch(
            dot_path, return_value=(tmp_path / 'minters').resolve(),
        )

    return tmp_path


@pytest.fixture()
def minters(tmp_bdb_root, reloaded):
    """Add four ready to use minters below the temporary root created by
    tmp_bdb_root.

    Returns a list containing the IdNamespace objects for the shoulders
    of the minters.
    """
    for ns, arg_tup in NAMESPACE_LIST:
        nog.shoulder.create_shoulder(
            ns,
            'test org for shoulder {}'.format(str(ns)),
            datacenter_model=(
                ezidapp.models.store_datacenter.StoreDatacenter.objects.filter(
                    symbol='CDL.CDL'
                ).get()
                if 'datacenter' in arg_tup
                else None
            ),
            is_crossref='crossref' in arg_tup,
            is_test=True,
            is_super_shoulder='supershoulder' in arg_tup,
            is_sharing_datacenter=False,
            is_force='force' in arg_tup,
            is_debug=True,
        )

    reloaded()
    return NAMESPACE_LIST


@pytest.fixture()
def shoulder_csv():
    """Generator returning rows from the SHOULDER_CSV file."""

    def itr():
        with pathlib2.Path(SHOULDER_CSV).open('rb',) as f:
            for row_tup in csv.reader(f):
                ns_str, org_str, n2t_url = (s.decode('utf-8') for s in row_tup)
                # log.debug('Testing with shoulder row: {}'.format(row_tup))
                yield ns_str, org_str, n2t_url

    return itr()


@pytest.fixture()
def test_docs():
    """pathlib2.Path rooted in the test_docs dir."""
    return pathlib2.Path(nog.filesystem.abs_path('./test_docs'))


@pytest.fixture()
def log_shoulder_count():
    # noinspection PyProtectedMember
    def log_(s):
        log.debug(
            '{}: db_shoulders={} cache_shoulders={}'.format(
                s,
                ezidapp.models.Shoulder.objects.filter(
                    active=True, manager='ezid'
                ).count(),
                len(ezidapp.models.shoulder._shoulders),
            )
        )

    log_('Shoulders before test launch')
    return log_


# Util


def dump_shoulder_table():
    for shoulder_model in ezidapp.models.Shoulder.objects.filter(
        active=True, manager='ezid'
    ):
        log.debug(shoulder_model)


def get_user_id_by_session_key(session_key):
    session_model = django.contrib.sessions.models.Session.objects.get(pk=session_key)
    session_dict = session_model.get_decoded()
    return session_dict['_auth_user_id']


def django_save_db_fixture(db_key=DEFAULT_DB_KEY):
    """Save database to a bz2 compressed JSON fixture."""
    fixture_file_path = nog.filesystem.abs_path(REL_DB_FIXTURE_PATH)
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
