"""EZID settings
"""
#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import collections
import logging.config
import os
import pathlib
import socket
import sys

import django.db.models
import django.utils.translation

import impl.nog.tb


def my_excepthook(type, value, traceback):
    impl.nog.tb.traceback_with_local_vars(type, value, traceback)
    # print ('Unhandled error:', type, value)

# print('Installing exception hook')
# sys.excepthook = my_excepthook

# When DEBUG == True, any errors in EZID are returned to the user as pages containing
# full stack traces and additional information. Should only be used for development.
DEBUG = True

# When STANDALONE == True, Django handles serving of static files. Should only be used
# for development.
# TODO: Fix 'index out of range' when set to True
STANDALONE = False

# Absolute paths

# Dirs at or below PROJECT_ROOT
# Create an absolute path to project dir. The project dir is the root dir of the EZID
# repository. It holds the settings, impl, and ezidapp dirs.
# /apps/ezid/ezid
SITE_ROOT = PROJECT_ROOT = pathlib.Path(__file__).parent.parent.resolve()
SETTINGS_DIR = PROJECT_ROOT / 'settings'  # /apps/ezid/ezid/settings
TEMPLATE_DIR = PROJECT_ROOT / 'templates'  # /apps/ezid/ezid/templates

# Dirs above PROJECT_ROOT
HOME_DIR = (PROJECT_ROOT / '..').resolve()  # /apps/ezid
MINTERS_PATH = HOME_DIR / 'var' / 'minters'  # /apps/ezid/var/minters

ROOT_URLCONF = 'settings.urls'

# Download
# URL paths
DOWNLOAD_WORK_URL = '/static/download/'
DOWNLOAD_PUBLIC_URL = '/static/download/public'
# Filesystem paths
DOWNLOAD_WORK_DIR = HOME_DIR / 'download'  # /apps/ezid/download
DOWNLOAD_PUBLIC_DIR = DOWNLOAD_WORK_DIR / 'public'  # /apps/ezid/download/public

# URL path to root of static files.
STATIC_URL = '/static/'
# Filesystem path to root of static files.
# Static files are collected into STATIC_URL by `./manage.py collectstatic`
STATIC_ROOT = PROJECT_ROOT / 'static'  # /apps/ezid/ezid/static
# List of locations for `collectstatic` to search.
LOCALE_PATHS = [STATIC_ROOT / 'locale']  # /apps/ezid/ezid/locale

STATICFILES_DIRS = [
    PROJECT_ROOT / 'static_src',
]

# Async processing daemons

# DAEMONS_ENABLED:
#   - True: Always enable daemon threads
#   - False: Always disable daemon threads
#   - 'auto': Enable daemon threads only if process is running under Apache /
#      mod_wsgi.
DAEMONS_ENABLED = True

assert DAEMONS_ENABLED in (True, False, 'auto')
if DAEMONS_ENABLED == 'auto':
    DAEMONS_ENABLED = os.environ.get('IS_RUNNING_UNDER_MOD_WSGI', False)

# The following enablement flags are subservient to the DAEMONS_ENABLED Django
# setting.
DAEMONS_SEARCHDB_ENABLED = True
DAEMONS_NEWSFEED_ENABLED = True
DAEMONS_STATUS_ENABLED = True
DAEMONS_BINDER_ENABLED = True
DAEMONS_DATACITE_ENABLED = True
DAEMONS_CROSSREF_ENABLED = True
DAEMONS_DOWNLOAD_ENABLED = True
DAEMONS_LINKCHECK_UPDATE_ENABLED = True
DAEMONS_LINKCHECKER_ENABLED = True

DAEMONS_BACKGROUND_PROCESSING_IDLE_SLEEP = 5
DAEMONS_STATUS_LOGGING_INTERVAL = 1  ################# 60
DAEMONS_BINDER_PROCESSING_IDLE_SLEEP = 5
DAEMONS_BINDER_PROCESSING_ERROR_SLEEP = 300
DAEMONS_BINDER_NUM_WORKER_THREADS = 3
DAEMONS_DATACITE_PROCESSING_IDLE_SLEEP = 5
DAEMONS_DATACITE_PROCESSING_ERROR_SLEEP = 300
DAEMONS_DATACITE_NUM_WORKER_THREADS = 3
DAEMONS_CROSSREF_PROCESSING_IDLE_SLEEP = 60
DAEMONS_DOWNLOAD_PROCESSING_IDLE_SLEEP = 10
DAEMONS_STATISTICS_COMPUTE_CYCLE = 3600
DAEMONS_STATISTICS_COMPUTE_SAME_TIME_OF_DAY = True

MAX_CONCURRENT_OPERATIONS_PER_USER = 4
MAX_THREADS_PER_USER = 16

# DB

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': 'localhost',
        "NAME": "test3", # TODO: Revert to regular DB
        # "NAME": "ezid_test_db",
        'USER': 'ezid_test_user',
        "PASSWORD": '',
        'PORT': '3306',
        'OPTIONS': {'charset': 'utf8mb4'},
        'ATOMIC_REQUESTS': False,
        'AUTOCOMMIT': True,
        'CONN_MAX_AGE': 0,
        'TIME_ZONE': None,
        'TEST': {
            'CHARSET': None,
            'COLLATION': None,
            'NAME': None,
            'MIRROR': None,
        },
    },
}

DATABASES['search'] = DATABASES['default'].copy()
DATABASES['search']['fulltextSearchSupported'] = True

DATABASES_RECONNECT_DELAY = 60

# The options in this section are used only if fulltext search is supported by the
# search database.  The following two options could be obtained from MySQL directly, but
# we put them here to avoid any overt dependencies on MySQL.
SEARCH_MINIMUM_WORD_LENGTH = 3
SEARCH_STOPWORDS = (
    'about are com for from how that the this was what when where who will with und www'
)

# The following additional stopwords, determined empirically, are the words that appear
# in the keyword text of more than 20% of identifiers.
SEARCH_EXTRA_STOPWORDS = (
    'http https ark org cdl cdlib doi merritt lib ucb dataset and data edu 13030 type '
    'version systems inc planet conquest 6068 datasheet servlet dplanet dataplanet '
    'statisticaldatasets'
)

# Email

if 'HOSTNAME' in os.environ:
    SERVER_EMAIL = 'ezid@' + os.environ['HOSTNAME']
else:
    SERVER_EMAIL = 'ezid@' + socket.gethostname()

EMAIL_NEW_ACCOUNT_EMAIL = 'invalid@invalid.invalid'

# Error notification emails sufficiently similar to previously-sent
# emails are suppressed for 'error_suppression_window' seconds; the
# timer is completely reset after 'error_lifetime' seconds.  Two
# emails are sufficiently similar if their similarity ratio is greater
# than or equal to 'error_similarity_threshold'.
EMAIL_ERROR_SUPPRESSION_WINDOW = 3600
EMAIL_ERROR_LIFETIME = 14400
EMAIL_ERROR_SIMILARITY_THRESHOLD = 0.6

# EZID errors are automatically emailed to this list.
MANAGERS = ADMINS = []

# Logging

# Disable Django's built-in logging config
LOGGING_CONFIG = None

# Disable EZID's logging config (would be performed in impl.log)
LOGGING_CONFIG_FILE = None

# Configure logging directly, overriding any existing config
logging.config.dictConfig(
    {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': (
                    '%(levelname)8s %(name)8s %(module)s '
                    '%(process)d %(thread)s %(message)s'
                ),
            },
            'simple': {'format': '%(levelname)8s %(message)s'},
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
                # 'formatter': 'simple',
                # 'stream': sys.stdout,
            },
        },
        'loggers': {
            '': {
                'handlers': ['console'],
                'propagate': True,
                'level': 'DEBUG', # 'INFO'
            },
            # Increase logging level on loggers that are noisy at debug level
            # Note: django.server logs at warning level for 404s.
            'django.server': {
                'level': 'DEBUG',
                # 'level': 'ERROR',
            },
            'django.db': {
                'level': 'DEBUG',
                # 'level': 'ERROR',
            },
            'django.request': {
                'level': 'ERROR',
            },
            # TODO: Look into messages about missing variables in templates
            'django.template': {
                'level': 'INFO',
            },
            'filelock': {
                'level': 'ERROR',
            },
            'django.utils.autoreload': {
                'level': 'ERROR',
            },
            # Suppress 'Using selector: EpollSelector'
            'asyncio': {
                'level': 'WARNING',
            },
        },
    }
)

# Server instance

EZID_BASE_URL = 'https://ezid.cdlib.org'
ALLOWED_HOSTS = ['*']
SECRET_KEY = 'nb6@8#38y4o)^!b&*ax(zy-cpf^%a^t=#@uk+4j*q7ho09m6=9'

# i18n / locale

LANGUAGES = [
    ('en', django.utils.translation.gettext_lazy('English')),
    ('fr-CA', django.utils.translation.gettext_lazy('Canadian French')),
]
LANGUAGE_CODE = 'en'
LOCALIZATIONS = {'default': ('cdl', ['ezid@ucop.edu'])}

TIME_ZONE = 'America/Los_Angeles'
TIME_FORMAT_UI_METADATA = '%Y-%m-%d %H:%M:%S'

# News feed

NEWSFEED_URL = (
    'http://www.cdlib.org/cdlinfo/category/infrastructure-services/ezid/feed/'
)
NEWSFEED_POLLING_INTERVAL = 1800

# Sessions

SESSION_COOKIE_AGE = 7 * 24 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'
SESSION_COOKIE_PATH = '/'

# EZID administrator account

# Note: The `diag-apply-admin-password` management command must be run in order to apply
# changes made to any of the `ADMIN_` settings. E.g.,
#
# $ cd ezid
# $ ./manage.py diag-apply-admin-password

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'
ADMIN_GROUPNAME = 'admin'
ADMIN_NOTES = 'This user owns 1 identifier under former shoulder doi:10.5060/D2'
ADMIN_EMAIL = 'ezid@ucop.edu'
ADMIN_DISPLAY_NAME = 'EZID superuser'

ADMIN_ORG_ACRONYM = 'CDL'
ADMIN_ORG_NAME = 'EZID'
ADMIN_ORG_URL = 'http://ezid.cdlib.org/'

ADMIN_CROSSREF_EMAIL = ''
ADMIN_CROSSREF_ENABLED = False

ADMIN_PRIMARY_CONTACT_EMAIL = 'ezid@ucop.edu'
ADMIN_PRIMARY_CONTACT_NAME = 'EZID superuser'
ADMIN_PRIMARY_CONTACT_PHONE = '(510) 987-0555'

ADMIN_SECONDARY_CONTACT_EMAIL = 'ezid@ucop.edu'
ADMIN_SECONDARY_CONTACT_NAME = 'EZID superuser'
ADMIN_SECONDARY_CONTACT_PHONE = '(510) 987-0555'

ADMIN_STORE_REALM = 'CDL'
ADMIN_STORE_USER_PID = 'ark:/99166/p9kw57h4w'
ADMIN_STORE_GROUP_PID = 'ark:/99166/p9g44hq02'

ADMIN_SEARCH_REALM = 'CDL'
ADMIN_SEARCH_USER_PID = 'ark:/99166/p9kw57h4w'
ADMIN_SEARCH_GROUP_PID = 'ark:/99166/p9g44hq02'

# Credentials

ARK_PROFILE = 'erc'
DOI_PROFILE = 'datacite'
UUID_PROFILE = 'erc'

GOOGLE_ANALYTICS_ID = None

GZIP_COMMAND = '/usr/bin/gzip'
ZIP_COMMAND = '/usr/bin/zip'

BINDER_URL = 'https://n2t-stg.n2t.net/a/ezid/b'
BINDER_USERNAME = 'ezid'
BINDER_PASSWORD = ''
BINDER_NUM_ATTEMPTS = 3
BINDER_REATTEMPT_DELAY = 5

# The ARK resolvers correspond to the above binders.
RESOLVER_DOI = 'https://doi.org'
RESOLVER_ARK = 'https://n2t-stg.n2t.net'

# Shoulders
SHOULDERS_ARK_TEST = 'ark:/99999/fk4'
SHOULDERS_DOI_TEST = 'doi:10.5072/FK2'
SHOULDERS_CROSSREF_TEST = 'doi:10.15697/'
SHOULDERS_AGENT = 'ark:/99166/p9'

TEST_SHOULDER_DICT = [
    {"namespace": 'ARK Test', "prefix": SHOULDERS_ARK_TEST},
    {"namespace": 'DOI Test', "prefix": SHOULDERS_DOI_TEST},
]

# DataCite

DATACITE_ENABLED = False
DATACITE_DOI_URL = 'https://mds.datacite.org/doi'
DATACITE_METADATA_URL = 'https://mds.datacite.org/metadata'

DATACITE_NUM_ATTEMPTS = 3
DATACITE_REATTEMPT_DELAY = 5
DATACITE_TIMEOUT = 60
DATACITE_PING_DOI = '10.5060/D2_EZID_STATUS_CHECK'
DATACITE_PING_DATACENTER = 'CDL.CDL'
DATACITE_PING_TARGET = 'http://ezid.cdlib.org/'
DATACITE_ALLOCATORS = 'CDL,PURDUE'

# Allocator

ALLOCATOR_CDL_PASSWORD = ''
ALLOCATOR_PURDUE_PASSWORD = ''

# Crossref

# The 'daemons.crossref_enabled' flag governs whether the Crossref
# daemon thread runs.  The flag below governs if the daemon actually
# contacts Crossref, or if Crossref calls are simply short-circuited.
CROSSREF_ENABLED = False
CROSSREF_DEPOSITOR_NAME = 'EZID'
CROSSREF_DEPOSITOR_EMAIL = 'ezidcdl@gmail.com'
CROSSREF_REAL_SERVER = 'doi.crossref.org'
CROSSREF_TEST_SERVER = 'test.crossref.org'
CROSSREF_DEPOSIT_URL = 'https://%%s/servlet/deposit'
CROSSREF_RESULTS_URL = 'https://%%s/servlet/submissionDownload'
CROSSREF_USERNAME = ''
CROSSREF_PASSWORD = ''

# Profiles

# Note: the INTERNAL profile is special and must be listed first.
PROFILES_KEYS = 'INTERNAL,DATACITE,DC,ERC,CROSSREF'
PROFILE_INTERNAL_NAME = 'internal'
PROFILE_INTERNAL_DISPLAY_NAME = 'internal'
PROFILE_INTERNAL_EDITABLE = False
PROFILE_INTERNAL_FILE = PROJECT_ROOT / 'profiles' / 'internal.profile'

PROFILE_DATACITE_NAME = 'datacite'
PROFILE_DATACITE_DISPLAY_NAME = 'DataCite'
PROFILE_DATACITE_EDITABLE = True
PROFILE_DATACITE_FILE = PROJECT_ROOT / 'profiles' / 'datacite.profile'

PROFILE_DC_NAME = 'dc'
PROFILE_DC_DISPLAY_NAME = 'Dublin Core'
PROFILE_DC_EDITABLE = True
PROFILE_DC_FILE = PROJECT_ROOT / 'profiles' / 'dc.profile'

PROFILE_ERC_NAME = 'erc'
PROFILE_ERC_DISPLAY_NAME = 'ERC'
PROFILE_ERC_EDITABLE = True
PROFILE_ERC_FILE = PROJECT_ROOT / 'profiles' / 'erc.profile'

PROFILE_CROSSREF_NAME = 'crossref'
PROFILE_CROSSREF_DISPLAY_NAME = 'Crossref'
PROFILE_CROSSREF_EDITABLE = False
PROFILE_CROSSREF_FILE = PROJECT_ROOT / 'profiles' / 'crossref.profile'

OAI_ENABLED = True
OAI_REPOSITORY_NAME = 'EZID'
OAI_ADMIN_EMAIL = 'ezid@ucop.edu'
OAI_BATCH_SIZE = 100

CLOUDWATCH_ENABLED = True
CLOUDWATCH_REGION = 'us-west-2'
CLOUDWATCH_NAMESPACE = 'EZID'
CLOUDWATCH_INSTANCE_NAME = 'uc3-ezidx2-dev'

# Linkchecker

# How often the link checker table is updated from the main EZID tables; new and updated
# identifiers will not be detected by the link checker more frequently than this.
LINKCHECKER_TABLE_UPDATE_CYCLE = 604800
# The converse, how often link checker results are incorporated back into the main EZID
# tables.
LINKCHECKER_RESULTS_UPLOAD_CYCLE = 3600
# If 'RESULTS_UPLOAD_SAME_TIME_OF_DAY' is True, then link checker results are
# incorporated back once a day, and 'RESULTS_UPLOAD_CYCLE' is interpreted as an offset
# from midnight. 'GOOD_RECHECK_MIN_INTERVAL' is the minimum elapsed time between
# successive checks of a good link.
LINKCHECKER_RESULTS_UPLOAD_SAME_TIME_OF_DAY = True
LINKCHECKER_GOOD_RECHECK_MIN_INTERVAL = 2592000
LINKCHECKER_BAD_RECHECK_MIN_INTERVAL = 187200
# Minimum elapsed time between successive checks against any given owner's links.
LINKCHECKER_OWNER_REVISIT_MIN_INTERVAL = 5
# Number of consecutive failures that must occur before the failure is considered
# notification-worthy.
LINKCHECKER_NOTIFICATION_THRESHOLD = 7
LINKCHECKER_NUM_WORKERS = 6
# Maximum number of links retrieved from the database per owner per round of checking.
LINKCHECKER_WORKSET_OWNER_MAX_LINKS = 500
LINKCHECKER_CHECK_TIMEOUT = 30
LINKCHECKER_USER_AGENT = 'EZID (EZID link checker; https://ezid.cdlib.org/)'
# The following governs the number of bytes to read from any given
# link.  Set to a negative value to make unlimited.
LINKCHECKER_MAX_READ = 104857600

# Internal settings

# Changes in these settings may require corresponding source code modifications.

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

INSTALLED_APPS = [
    'django_extensions',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'ui_tags',
    'ezidapp',
]

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

MIDDLEWARE = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'impl.middleware.ExceptionScrubberMiddleware',
)

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'impl.userauth.LdapSha1PasswordHasher',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATE_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
            ]
        },
    }
]


QUERY_PAGE_SIZE = 10000

BlobField = collections.namedtuple(
    'BlobField', ['model', 'field', 'is_queue']
)

BLOB_FIELD_LIST = [
    # metadata = Python, JSON, and legacy compound objects
    BlobField('BinderQueue', 'metadata', True),
    BlobField('CrossrefQueue', 'metadata', True),
    BlobField('DataciteQueue', 'metadata', True),

    # object = Identifier (Model)
    BlobField('DownloadQueue', 'object', True),

    # cm = CompressedJsonField (Field)
    BlobField('Identifier', 'cm', False),
    BlobField('Identifier', 'cm', False),

    BlobField('LinkChecker', '', False),
]

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# SERIALIZATION_MODULES = {
#     'extjson': 'ezidapp.models.serialization',
# }


# From django_extensions

# BASE_DIR = os.path.dirname(os.path.realpath(__file__))
# REPLACEMENTS = getattr(settings, 'EXTENSIONS_REPLACEMENTS', {})
#
# DEFAULT_SQLITE_ENGINES = (
#     'django.db.backends.sqlite3',
#     'django.db.backends.spatialite',
# )
# DEFAULT_MYSQL_ENGINES = (
#     'django.db.backends.mysql',
#     'django.contrib.gis.db.backends.mysql',
#     'mysql.connector.django',
# )
# DEFAULT_POSTGRESQL_ENGINES = (
#     'django.db.backends.postgresql',
#     'django.db.backends.postgresql_psycopg2',
#     'django.db.backends.postgis',
#     'django.contrib.gis.db.backends.postgis',
#     'psqlextra.backend',
#     'django_zero_downtime_migrations.backends.postgres',
#     'django_zero_downtime_migrations.backends.postgis',
# )
#
# SQLITE_ENGINES = getattr(settings, 'DJANGO_EXTENSIONS_RESET_DB_SQLITE_ENGINES', DEFAULT_SQLITE_ENGINES)
# MYSQL_ENGINES = getattr(settings, 'DJANGO_EXTENSIONS_RESET_DB_MYSQL_ENGINES', DEFAULT_MYSQL_ENGINES)
# POSTGRESQL_ENGINES = getattr(settings, 'DJANGO_EXTENSIONS_RESET_DB_POSTGRESQL_ENGINES', DEFAULT_POSTGRESQL_ENGINES)
