import bz2
import io
import logging

import django
import django.conf
import django.contrib.auth.models
import django.contrib.sessions.models
import django.core.management
import django.db
import django.db.transaction
import django.http.request
import pytest

import ezidapp
import ezidapp.models
import impl.config
import impl.config
import impl.userauth
import tests.util.util
import utils.filesystem

DEFAULT_DB_KEY = 'default'
import collections

Namespace = collections.namedtuple('Namespace', ['full', 'prefix', 'shoulder'])

NAMESPACE_LIST = [
    Namespace('ark:/99933/x1', '99933', 'x1'),
    Namespace('ark:/99934/x2', '99934', 'x2'),
    Namespace('doi:10.9935/x3', '9935', 'x3'),
    Namespace('doi:10.9996/x4', '9996', 'x4'),
]

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


@pytest.fixture(scope='function')
def admin_admin(db):
    """Set the admin password to "admin".
    """
    with django.db.transaction.atomic():
        if not django.contrib.auth.models.User.objects.filter(
            username='admin'
        ).exists():
            django.contrib.auth.models.User.objects.create_superuser(
                username='admin', password=None, email=""
            )
        o = ezidapp.models.getUserByUsername('admin')
        o.setPassword('admin')
        o.save()


@pytest.fixture(scope='function')
def configured(db):
    """EZID's in-memory caches are loaded and valid."""
    impl.config.reload()


@pytest.fixture(scope='function')
def ez_admin(admin_client, admin_admin, configured, mocker):
    admin_client.login(username='admin', password='admin')
    # print('cookies={}'.format(admin_client.cookies))
    mocker.patch('userauth.authenticateRequest', side_effect=mock_authenticate_request)
    return admin_client


def get_user_id_by_session_key(session_key):
    session_model = django.contrib.sessions.models.Session.objects.get(pk=session_key)
    session_dict = session_model.get_decoded()
    # {'_auth_user_hash': '0fe96656c9ff4037ee12ec236e1936fc6b18d851',
    #  '_auth_user_id': u'1',
    #  '_auth_user_backend': u'django.contrib.auth.backends.ModelBackend'}
    return session_dict['_auth_user_id']


def mock_authenticate_request(request, storeSessionCookie=False):
    print('-' * 100)
    print('mock_authenticate_request')
    user_id = get_user_id_by_session_key(request.session.session_key)
    return ezidapp.models.getUserById(user_id)


@pytest.fixture(scope='session')
def django_db_setup(django_db_keepdb):
    django.conf.settings.DATABASES = {
        # To keep the Django admin app happy, the store database must be
        # referred to as 'default', despite our use of a router below.
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "HOST": "localhost",
            "NAME": "ezid_tests",
            "USER": "ezid_test_user",
            "PASSWORD": "",
            "OPTIONS": {"charset": "utf8mb4"},
        },
        "search": {
            "ENGINE": "django.db.backends.mysql",
            "HOST": "localhost",
            "NAME": "ezid_tests",
            "USER": "ezid_test_user",
            "PASSWORD": "",
            "OPTIONS": {"charset": "utf8mb4"},
            "fulltextSearchSupported": True,
        },
    }


# @pytest.fixture(scope='session')
# def django_db_setup(django_db_setup, django_db_blocker):
#     """Populate the database from a fixture.
#     Note: The double "django_db_setup" in the signature is correct.
#     """
#     with django_db_blocker.unblock():
#         if '--create-db' in sys.argv:
#             # We can modify the DB settings here because the django_db_setup fixture
#             # includes django_db_modify_db_settings. We use this to prevent pytest
#             # from generating a new name.
#             django.conf.settings.DATABASES['default']['NAME'] = 'ezid_tests'
#
#             # log.debug(
#             #     'Using database: {}'.format(django.conf.settings.DATABASES['default']['NAME'])
#             # )
#
#             # with django.db.transaction.atomic():
#             django.core.management.call_command(
#                 'loaddata', 'combined-limited', '--settings', 'settings.test_settings',
#             )
#
#             # Read admin username and password from config file and create a hashed
#             # password entry in the DB.
#             # impl.config.load()
#             # u = impl.config.get("auth.admin_username")
#             # p = impl.config.get("auth.admin_password")
#             u = 'admin'
#             p = 'admin'
#             # with django.db.transaction.atomic():
#
#             if not django.contrib.auth.models.User.objects.filter(
#                 username=u
#             ).exists():
#                 django.contrib.auth.models.User.objects.create_superuser(
#                     username=u, password=None, email=""
#                 )
#             o = ezidapp.models.getUserByUsername(u)
#             o.setPassword(p)
#             o.save()
#
#         # log.debug('Using database: {}'.format(settings.DATABASES['default']['NAME']))
#         # log.debug('Using database: {}'.format(django.conf.settings.DATABASES['default']['NAME']))
#         # log.debug('Shoulders: {}'.format(ezidapp.models.Shoulder.objects.count()))
#         # log.debug(
#         #     'Identifiers: {}'.format(ezidapp.models.StoreIdentifier.objects.count())
#         # )
#         #
#         # yield
#         #
#         # for connection in django.db.connections.all():
#         #     connection.close()


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Make the Django DB available to all tests. This will use Django's default DB,
    which is the "store" DB in EZID. The DB connection is set up according to the
    DJANGO_SETTINGS_MODULE setting in ezid/tox.ini.
    """
    pass


@pytest.fixture()
def tmp_bdb_root(mocker, tmp_path):
    """Temporary root for the BerkeleyDB minters.

    Returns: :class:`pathlib.Path`

    Causes nog_minter to see an empty tree of minters rooted in temp. Any minters
    created by the test are deleted when the test exits.
    """
    mocker.patch(
        'nog_minter.get_bdb_root',
        return_value=(tmp_path / 'minters').resolve().as_posix(),
    )
    mocker.patch(
        'impl.nog_minter.get_bdb_root',
        return_value=(tmp_path / 'minters').resolve().as_posix(),
    )
    for i, namespace_str in enumerate(NAMESPACE_LIST):
        tests.util.util.create_shoulder(
            namespace_str.full,
            'test org {}'.format(i),
            tmp_path.as_posix() + '/minters',
        )

    impl.config.reload()

    return tmp_path, NAMESPACE_LIST


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
