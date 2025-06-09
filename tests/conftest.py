#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import base64
import bz2
import collections
import csv
import datetime
import io
import json
import logging
import os
import pathlib
import re
import sys
import types

import django
import django.apps
import django.conf
import django.contrib.auth.models
import django.contrib.sessions.models
import django.core.management
import django.db
import django.db.transaction
import django.http.request
import django.test.client
import pytest

import ezidapp
# Queues
import ezidapp.models.async_queue
import ezidapp.models.async_queue
import ezidapp.models.datacenter
import ezidapp.models.link_checker
import ezidapp.models.shoulder
import ezidapp.models.user
import ezidapp.models.util
import impl.nog_sql.filesystem
import impl.nog_sql.ezid_minter
import impl.nog_sql.shoulder
import tests.util.metadata_generator
import tests.util.sample
import tests.util.util

APP_LABEL = 'ezidapp'

HERE_PATH = pathlib.Path(__file__).parent.resolve()
ROOT_PATH = HERE_PATH / '..'

DEFAULT_DB_KEY = 'default'
import impl.nog_sql.id_ns

NS = impl.nog_sql.id_ns.IdNamespace

# fmt=off
NAMESPACE_LIST = [
    # todo: commented out for faster testing
    (NS.from_str('ark:/99933/x1'), tuple()),
    # (NS.from_str('ark:/99934/x2'), tuple()),
    # (NS.from_str('ark:/99933/x3y4/'), ('supershoulder',)),
    # (NS.from_str('ark:/99934/'), ('supershoulder', 'force')),
    (NS.from_str('doi:10.9935/X5'), tuple()),
    # (NS.from_str('doi:10.19936/X6Y7'), tuple()),
    # (NS.from_str('doi:10.9935/X8'), tuple()),
    # (NS.from_str('doi:10.19936/X9Y0'), tuple()),
    # Shoulder for the API Test Account
    # (NS.from_str('doi:10.39999/SD2'), ()),
]
# fmt=on
META_TYPE_LIST = [
    'datacite',
    # todo: commented out for faster testing
    'crossref',
    # 'dc',
    # 'unknown',
]

TEST_DOCS_PATH = HERE_PATH / 'test_docs'
SHOULDER_CSV = TEST_DOCS_PATH / 'ezidapp_shoulder.csv'

METADATA_CSV = TEST_DOCS_PATH / 'metadata_samples.csv'


NOW_TS = datetime.datetime.now()


ADMIN_MODEL_DICT = {
    # Django standard user authentication
    'auth.user': {
        'date_joined': NOW_TS,
        'email': django.conf.settings.ADMIN_EMAIL,
        'first_name': django.conf.settings.ADMIN_DISPLAY_NAME,
        'is_active': True,
        'is_staff': True,
        'is_superuser': True,
        'last_login': NOW_TS,
        'last_name': '',
        # 'username': django.conf.settings.ADMIN_USERNAME,
        'password': django.conf.settings.ADMIN_PASSWORD,
    },
    'contenttypes.contenttype': {
        'app_label': 'admin',
        'model': 'logentry',
    },
    # EZID custom user authentication
    'ezidapp.Realm': {
        "name": django.conf.settings.ADMIN_REALM,
    },
    'ezidapp.user': {
        'pid': django.conf.settings.ADMIN_USER_PID,
        'username': django.conf.settings.ADMIN_USERNAME,
        'accountEmail': django.conf.settings.ADMIN_EMAIL,
        'crossrefEmail': django.conf.settings.ADMIN_CROSSREF_EMAIL,
        'crossrefEnabled': django.conf.settings.ADMIN_CROSSREF_ENABLED,
        'displayName': django.conf.settings.ADMIN_DISPLAY_NAME,
        'inheritGroupShoulders': False,
        'isGroupAdministrator': False,
        'isRealmAdministrator': False,
        'isSuperuser': True,
        'loginEnabled': True,
        'notes': django.conf.settings.ADMIN_NOTES,
        # 'password': django.conf.settings.ADMIN_PASSWORD,
        'primaryContactEmail': django.conf.settings.ADMIN_PRIMARY_CONTACT_EMAIL,
        'primaryContactName': django.conf.settings.ADMIN_PRIMARY_CONTACT_NAME,
        'primaryContactPhone': django.conf.settings.ADMIN_PRIMARY_CONTACT_PHONE,
        'secondaryContactEmail': django.conf.settings.ADMIN_SECONDARY_CONTACT_EMAIL,
        'secondaryContactName': django.conf.settings.ADMIN_SECONDARY_CONTACT_NAME,
        'secondaryContactPhone': django.conf.settings.ADMIN_SECONDARY_CONTACT_PHONE,
    },
    'ezidapp.group': {
        'accountType': '',
        'agreementOnFile': False,
        'crossrefEnabled': django.conf.settings.ADMIN_CROSSREF_ENABLED,
        'groupname': django.conf.settings.ADMIN_GROUPNAME,
        'notes': django.conf.settings.ADMIN_NOTES,
        'organizationAcronym': django.conf.settings.ADMIN_ORG_ACRONYM,
        'organizationName': django.conf.settings.ADMIN_ORG_NAME,
        'organizationStreetAddress': '(:unap)',
        'organizationUrl': django.conf.settings.ADMIN_ORG_URL,
        'pid': django.conf.settings.ADMIN_GROUP_PID,
    },
}


# Lists generated from CSV files
# - These are used for parametrizing fixtures, meaning that the test is run for each row in the CSV,
# and each run counts as a separate test.
# - Using multiple parametrizing fixtures causes the test to be run for each possible
# combination of the parameters.

def _csv_gen(csv_path, delimiter=','):
    """Generator that yields the rows from a CSV file"""
    with pathlib.Path(csv_path).open('rt') as f:
        for row_tup in csv.reader(f, delimiter=delimiter):
            yield row_tup


Metadata = collections.namedtuple(
    'Metadata', ['lower_bound', 'row_id', 'length', 'json', 'as_dict']
)
METADATA_TUP = tuple(
    Metadata(*row_tup, json.loads(row_tup[-1]))
    for row_tup in _csv_gen(METADATA_CSV, delimiter='\t')
)

# Database fixtures

REL_DB_FIXTURE_PATH = ROOT_PATH / 'ezidapp/fixtures/db-fixture.json'

# We use pytest's CLI logging, so can clear out the handlers created by Django here.
# if logging.getLogger().hasHandlers():
#     logging.getLogger().handlers.clear()

log = logging.getLogger(__name__)


# Hooks


def pytest_addoption(parser):
    parser.addoption(
        '--sample-error',
        dest='sample_error',
        action='store_true',
        default=False,
        help='Handle sample mismatch as test failure instead of opening diff viewer',
    )
    parser.addoption(
        '--sample-update',
        dest='sample_update',
        action='store_true',
        default=False,
        help='Update mismatched samples instead of opening diff viewer',
    )


# @pytest.fixture(autouse=True)
# def sample_options(request):
#     return types.SimpleNamespace(
#         error=request.config.getoption("--sample-error"),
#         update=request.config.getoption("--sample-update"),
#     )


def pytest_configure(config):
    """Allow plugins and conftest files to perform initial configuration

    This hook is called for every plugin and initial conftest file after command line
    options have been parsed.

    After that, the hook is called for other conftest files as they are imported.
    """
    sys.is_running_under_travis = "TRAVIS" in os.environ
    sys.is_running_under_pytest = True

    tests.util.sample.options = types.SimpleNamespace(
        error=config.getoption("--sample-error"),
        update=config.getoption("--sample-update"),
    )

    # Only accept error messages from loggers that are noisy at debug.
    logging.getLogger('django.db.backends.schema').setLevel(logging.ERROR)


# Autouse fixtures


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Make the Django DB available to all tests

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
    required. On Actions, this is done in `./.github/main.yml`.

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
            "NAME": "ezid_test_db",
            "USER": "ezid_test_user",
            "PASSWORD": "",
            "OPTIONS": {"charset": "utf8mb4"},
            'DATABASE_OPTIONS': {
                'unix_socket': '/tmp/mysql.sock',
            },
        },
    }


@pytest.fixture(autouse=True)
def disable_log_setup(mocker):
    """Prevent management commands from reconfiguring the logging that has been
    set up by pytest."""
    mocker.patch('impl.nog_sql.util.log_setup')


# Fixtures

# See also: https://pytest-django.readthedocs.io/en/latest/helpers.html#fixtures


@pytest.fixture(scope='function')
def admin_admin():
    """Set the admin password to "admin"

    This is intended for testing authentication. To instead skip authentication entirely,
    see skip_auth.
    """
    with django.db.transaction.atomic():
        if not django.contrib.auth.models.User.objects.filter(username='admin').exists():
            django.contrib.auth.models.User.objects.create_superuser(
                username='admin', password=None, email=""
            )
        o = ezidapp.models.util.getUserByUsername('admin')
        o.setPassword('admin')
        o.save()


# API Test Account

@pytest.fixture()
def apitest_minter():
    """Create a minter and corresponding shoulder for the apitest user

    The minter and shoulder are created in the DB read for use. The shoulders are
    registered to the admin user in the DB.
    """
    # ns_str = 'doi:10.39999/SD2'
    ns_str = 'ark:/99936/x3'

    shoulder_model = tests.util.util.create_shoulder_and_minter(
        namespace_str=ns_str,
        organization_name=f'API TEST Shoulder: {ns_str}',
        # datacenter_model=None,
        # is_crossref=True,
        # is_test=True,
        # is_super_shoulder=False,
        # is_sharing_datacenter=False,
        # is_force=False,
        # is_debug=True,
    )

    user_model = ezidapp.models.user.User.objects.get(username='apitest')

    tests.util.util.add_shoulder_to_user(shoulder_model, user_model)

    yield ns_str


@pytest.fixture(scope='function')
def apitest_client(client, django_user_model):
    """Django test client set up to call the EZID API and logged in as the apitest user

    This uses an existing user with username "apitest", or creates a new one with the same username.

    This also sets the password for the apitest user to 'apitest'.

    When EZID endpoints are called via the client, a cookie for an active authenticated session is
    included automatically.

    Because EZID does not use a standard authentication procedure, we can't use the regular
    'client.login()', which assumes standard Django auth.

    The password is salted, so the PBKDF hash that is stored in ezidapp_storeuser.password is
    different every time, even when using the same password:

        print(ezidapp.models.user.User.objects.get(username='apitest').password)

    TODO: This sort of procedure probably means that we no longer need 'skip_auth'.
    """
    username, password = 'apitest', 'apitest'

    # with django.db.transaction.atomic():

    django_user_model.objects.create_user(username=username, password=password)

    user = ezidapp.models.util.getUserByUsername(username)
    assert user is not None
    user.setPassword(password)
    user.save()

    is_logged_in = client.login(username=username, password=password)
    assert is_logged_in

    client.defaults['HTTP_AUTHORIZATION'] = b'Basic ' + base64.b64encode(
        b':'.join([username.encode('utf-8'), password.encode('utf-8')])
    )

    r = client.get(f'/login')
    assert r.status_code == 200

    return client


@pytest.fixture(scope='function')
def skip_auth(django_db_keepdb, admin_client, mocker):
    """Replace EZID's user authentication system with a stub that successfully
    authenticates any user.

    The user must already exist in EZID. By default, only the admin user
    exists.
    """

    def mock_authenticate_request(request):
        user_id = get_user_id_by_session_key(request.session.session_key)
        return ezidapp.models.util.getUserById(user_id)

    mocker.patch('impl.userauth.authenticateRequest', side_effect=mock_authenticate_request)


@pytest.fixture(scope='function')
def ez_admin(admin_client, admin_admin, skip_auth):
    """A Django test client that has been logged in as admin. When EZID
    endpoints are called via the client, a cookie for an active authenticated
    session is included automatically. This also sets the admin password to
    "admin".

    Because EZID does not use a standard authentication procedure:

        - It's necessary to pull in skip_auth here.

        - We can't use the regular 'client.login()', which assumes standard Django auth.

    """
    admin_client.login(username='admin', password='admin')
    # log.info('cookies={}'.format(admin_client.cookies))
    return admin_client


@pytest.fixture(scope='function')
def ez_user(client, django_user_model):
    """A Django test client that has been logged in as a regular user named
    "ezuser", with password "password".
    """
    username, password = "ezuser", "password"
    django_user_model.objects.create_user(username=username, password=password)
    client.login(username=username, password=password)
    return client


@pytest.fixture()
def minters(namespace, meta_type):
    """Add a set of minters and corresponding shoulders. 
    The minters and shoulders are created in the DB ready for use. 
    The shoulders are registered to the admin user in the DB.

    Yields a list containing the IdNamespace objects for the shoulders.

    `namespace` and `meta_type` are parameterized fixtures, causing this fixture to be invoked
    multiple times, creating minters that are the combinatorial product of the two.
    """
    ns, arg_tup = namespace
    impl.nog_sql.shoulder.create_shoulder(
        ns,
        'test org for shoulder {}'.format(str(ns)),
        datacenter_model=(
            ezidapp.models.datacenter.Datacenter.objects.filter(symbol='CDL.CDL').get()
            if meta_type == 'datacite'
            else None
        ),
        is_crossref=meta_type == 'crossref',
        is_test=True,
        is_super_shoulder='supershoulder' in arg_tup,
        is_sharing_datacenter=False,
        is_force='force' in arg_tup,
        is_debug=True,
    )
    yield namespace

@pytest.fixture()
def agent_minter():
    """Create the minter for the CDL Agent shoulder.
    
    The Agent shoulder (ark:/99166/p9) is already in the DB ready for use.
    Create the corresponding minter in the DB.
    """
    prefix = 'ark:/99166/p9'
    if not ezidapp.models.minter.Minter.objects.filter(
        prefix=prefix
    ).exists():
        impl.nog_sql.ezid_minter.create_minter_database(prefix)
    

@pytest.fixture()
def shoulder_csv():
    """Generator returning rows from the SHOULDER_CSV file."""

    def itr():
        with pathlib.Path(SHOULDER_CSV).open('rt') as f:
            for row_tup in csv.reader(f):
                ns_str, org_str, n2t_url = row_tup
                # log.debug('Testing with shoulder row: {}'.format(row_tup))
                yield ns_str, org_str, n2t_url

    return itr()


@pytest.fixture(
    params=NAMESPACE_LIST,
    ids=lambda x: re.sub(r"[^\d\w]+", "-", '-'.join([str(x[0]), *x[1]])),
)
def namespace(request):
    return request.param


@pytest.fixture(
    params=METADATA_TUP,
)
def metadata(request):
    """Parametrize on JSON encoded metadata

    The metadata is pulled from the METADATA_CSV file, which is a TSV, tab separated values /
    columns.

    Columns:
        - Lower bound of length of JSON encoded metadata (inclusive)
            - The upper bound for each JSON string is the next lower bound of the following row
            (exclusive).
        - Id sequence number from the Identifier table row holding the metadata that was
            selected for the sample
        - Length, in Unicode code points, of the JSON metadata (TODO: Or is it the number of UTF-8
            bytes, the implicit encoding for JSON?)
        - JSON encoded
        metadata
    """
    return request.param


@pytest.fixture()
def test_docs():
    """pathlib.Path rooted in the test_docs dir."""
    return TEST_DOCS_PATH


@pytest.fixture()
def log_shoulder_count():
    # noinspection PyProtectedMember
    def log_(s):
        log.debug(
            '{}: db_shoulders={}'.format(
                s,
                ezidapp.models.shoulder.Shoulder.objects.filter(
                    active=True, manager='ezid'
                ).count(),
            )
        )

    log_('Shoulders before test launch')
    return log_


@pytest.fixture(params=META_TYPE_LIST)
def meta_type(request):
    """A list of metadata types which trigger different types of validation in EZID. We
    test with specific metadata for each.
    """
    return request.param


@pytest.fixture()
def block_outgoing(mocker):
    mocker.patch('ezidapp.management.commands.proc_base.AsyncProcessingCommand.callWrapper')


@pytest.fixture()
def registration_queue(request):
    """BinderQueue populated with tasks marked as not yet processed"""
    django_load_db_fixture('ezidapp/fixtures/registration_queue.json')


# Queues


@pytest.fixture()
def registration_queue(request):
    """BinderQueue populated with tasks marked as not yet processed"""
    django_load_db_fixture('ezidapp/fixtures/registration_queue.json')


# ezidapp.models.registration_queue
# ezidapp.models.async_queue
# ezidapp.models.link_checker

# Util


def dump_models():
    """Print a list of registered models"""
    model_dict = {model.__name__: model for model in django.apps.apps.get_models()}
    print('Registered models:')
    for k, v in sorted(model_dict.items()):
        print(f'  {k:<20} {v}')


def dump_shoulder_table():
    for shoulder_model in ezidapp.models.shoulder.Shoulder.objects.filter(
        active=True, manager='ezid'
    ):
        log.debug(shoulder_model)


def get_user_id_by_session_key(session_key):
    session_model = django.contrib.sessions.models.Session.objects.get(pk=session_key)
    session_dict = session_model.get_decoded()
    return session_dict['_auth_user_id']


def django_save_db_fixture(db_key=DEFAULT_DB_KEY):
    """Save database to a bz2 compressed JSON fixture."""
    fixture_file_path = impl.nog_sql.filesystem.abs_path(REL_DB_FIXTURE_PATH.as_posix())
    log.info('Writing fixture. path="{}"'.format(fixture_file_path))
    buf = io.StringIO()
    django.core.management.call_command(
        "dumpdata",
        exclude=["auth.permission", "contenttypes"],
        database=db_key,
        stdout=buf,
    )
    with bz2.BZ2File(fixture_file_path, "w", buffering=1024 ** 2, compresslevel=9) as bz2_file:
        bz2_file.write(buf.getvalue().encode("utf-8"))


def django_load_db_fixture(rel_json_fixture_path, db_key=DEFAULT_DB_KEY):
    log.debug("Populating DB from compressed JSON fixture file. db_key={}".format(db_key))
    fixture_file_path = impl.nog_sql.filesystem.abs_path(rel_json_fixture_path.as_posix())
    django.core.management.call_command("loaddata", fixture_file_path, database=db_key)
    django_commit_and_close(db_key)


def django_migrate(db_key=DEFAULT_DB_KEY):
    log.debug("Applying DB migrations. db_key={}".format(db_key))
    django.core.management.call_command("migrate", "--run-syncdb", database=db_key)
    django_commit_and_close(db_key)


def django_clear_db(db_key=DEFAULT_DB_KEY):
    django.core.management.call_command("flush", interactive=False, database=db_key)


def django_commit_and_close(db_key=DEFAULT_DB_KEY):
    django_commit(db_key)
    django_close_all_connections()


def django_commit(db_key=DEFAULT_DB_KEY):
    django.db.connections[db_key].commit()


def django_close_all_connections():
    for connection in django.db.connections.all():
        connection.close()
    # TODO: Needed?
    django.db.connections.close_all()


