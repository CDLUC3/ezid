# Copyright©2021, Regents of the University of California
# http://creativecommons.org/licenses/BSD

"""EZID settings

"""

import logging.config
import os
import pathlib
import socket
import sys
import ecs_logging

import django.utils.translation

# When DEBUG == True, any errors in EZID are returned to the user as pages containing
# full stack traces and additional information. Should only be used for development.
DEBUG = True

# When STANDALONE == True, Django handles serving of static files. Should only be used
# for development.
STANDALONE = False

# Semantic versioning (SemVer) string that is returned by the getVersion API call.
# TODO: Show this in the UI as well
EZID_VERSION = 'TEST_INSTANCE'

# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': '127.0.0.1',
        'NAME': 'ezid_test_db',
        'USER': 'ezid_test_user',
        'PASSWORD': 'ezid_test_pw',
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

DATABASES_RECONNECT_DELAY = 60

# The options in this section are used only if fulltext search is supported by the
# search database. The following two options could be obtained from MySQL directly, but
# we put them here to avoid any overt dependencies on MySQL.
SEARCH_MINIMUM_WORD_LENGTH = 3

OPENSEARCH_BASE = 'http://opensearch.example.com'
OPENSEARCH_INDEX = 'ezid-test-index'
OPENSEARCH_USER = 'test-user'
OPENSEARCH_PASSWORD = 'test-password'

# fmt:off
SEARCH_STOPWORDS = [
    'about', 'are', 'com', 'for', 'from', 'how', 'that', 'the', 'this', 'was', 'what',
    'when',
    'where', 'who', 'will', 'with', 'und', 'www'
]
# fmt:on

# The following additional stopwords, determined empirically, are the words that appear
# in the keyword text of more than 20% of identifiers.
# fmt:off
SEARCH_STOPWORDS += [
    'http', 'https', 'ark', 'org', 'cdl', 'cdlib', 'doi', 'merritt', 'lib', 'ucb',
    'dataset',
    'and', 'data', 'edu', '13030', 'type', 'version', 'systems', 'inc', 'planet',
    'conquest',
    '6068', 'datasheet', 'servlet', 'dplanet', 'dataplanet', 'statisticaldatasets',
]
# fmt:on

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
LOG_DIR = HOME_DIR / 'logs'  # /apps/ezid/logs

ROOT_URLCONF = 'settings.urls'

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
# - True: Daemons (asynchronous processing tasks) that are enabled in the
#   DAEMONS_*_ENABLED settings listed below are available to be started. For a daemon
#   to be able to be started, both this setting and its individual setting must be set
#   to ENABLED (True). A daemon that is started without being enabled will stop without
#   modifying the system state in any way, with a message indicating the settings that
#   were used.
# - False: Daemons cannot run. They are disabled regardless of the DAEMONS_*_ENABLED
#   settings listed below.
# - 'auto': Set to True if EZID is running under Apache / mod_wsgi, False otherwise.
DAEMONS_ENABLED = True

assert DAEMONS_ENABLED in (True, False, 'auto')
if DAEMONS_ENABLED == 'auto':
    DAEMONS_ENABLED = os.environ.get('IS_RUNNING_UNDER_MOD_WSGI', False)

# DAEMONS_*_ENABLED:
# - True: The daemon is available to be started.
# - False: The daemon cannot run.
# - See the DAEMONS_ENABLED setting above.
DAEMONS_CROSSREF_ENABLED = True
DAEMONS_DATACITE_ENABLED = True
DAEMONS_DOWNLOAD_ENABLED = True
DAEMONS_EXPUNGE_ENABLED = True
DAEMONS_LINKCHECKER_ENABLED = True
DAEMONS_LINKCHECK_UPDATE_ENABLED = True
DAEMONS_NEWSFEED_ENABLED = True
DAEMONS_SEARCH_INDEXER_ENABLED = True
DAEMONS_STATISTICS_ENABLED = True
DAEMONS_STATUS_ENABLED = True

# Daemons: Shared settings
# Sleep between batches. This sleep is performed while there is still work to do. It
# is intended for making sure that a buggy process does not go into a tight loop that
# consumes a lot of resources.
DAEMONS_BATCH_SLEEP = 1
# Sleep after all batches are done. This sleep is performed when there is no more work
# to do, but new work is expected to be added shortly.
DAEMONS_IDLE_SLEEP = 1
# Reset database connections after this many seconds.
# When sleeping, if its been more than this many seconds since the
# last time the connection was reset, then reset database connections
# This significantly reduces the disconnect / connect activity of background
# processes and allows for a shorter DAEMONS_IDLE_SLEEP (suggest 1 second)
# This value can be set to zero to disable.
DAEMONS_IDLE_DB_RECONNECT = 600
# Sleep after the work is done, for use in processing that is not time critical.
DAEMONS_LONG_SLEEP = 60 * 60 * 24
# Limit the number of results in each queryset. This value becomes a LIMIT clause in the
# SQL query that pulls work from the queue.
DAEMONS_MAX_BATCH_SIZE = 100

# Daemons: Individual settings
DAEMONS_DOWNLOAD_PROCESSING_IDLE_SLEEP = 10
DAEMONS_DOWNLOAD_WORK_DIR = HOME_DIR / 'download'  # /apps/ezid/download
DAEMONS_DOWNLOAD_PUBLIC_DIR = DAEMONS_DOWNLOAD_WORK_DIR / 'public'  # /apps/ezid/download/public
DAEMONS_DOWNLOAD_FILE_LIFETIME = 60 * 60 * 24 * 7

DAEMONS_STATISTICS_COMPUTE_CYCLE = 3600
DAEMONS_STATISTICS_COMPUTE_SAME_TIME_OF_DAY = True

MAX_CONCURRENT_OPERATIONS_PER_USER = 4
MAX_THREADS_PER_USER = 16

DATABASES_RECONNECT_DELAY = 60

# Max age of test identifiers before they are deleted
DAEMONS_EXPUNGE_MAX_AGE_SEC = 60 * 60 * 24 * 14

# The options in this section are used only if fulltext search is supported by the
# search database. The following two options could be obtained from MySQL directly, but
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
# timer is completely reset after 'error_lifetime' seconds. Two
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
            'simple': {'format': '%(asctime)s %(levelname)8s %(message)s'},
            'verbose': {
                'format': (
                    '%(levelname)8s %(module)s '
                    '%(process)d %(thread)s %(message)s'
                ),
            },
            'trace': {
                'format': (
                    '%(asctime)s %(levelname)s '
                    '%(module)s.%(funcName)s:%(lineno)s: %(message)s'
                )
            },
            'ecs_logging': {
                'class': 'ecs_logging.StdlibFormatter',
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
                'stream': sys.stdout,
            },
            'request_log': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': LOG_DIR / 'request.log',
                'formatter': 'simple',
            },
            'trace_log': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': LOG_DIR / 'trace.log',
                'formatter': 'trace',
            },
            'ecs_json': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': LOG_DIR / 'ecs_json.log',
                'formatter': "ecs_logging"
            },
        },
        'loggers': {
            '': {
                'handlers': ['request_log', 'trace_log', 'ecs_json'],
                'propagate': True,
                'level': 'DEBUG',
            },
            # Increase logging level on loggers that are noisy at debug level
            # Note: django.server logs at warning level for 404s.
            'django.server': {
                # 'level': 'DEBUG',
                'level': 'ERROR',
            },
            'django.db': {
                # 'level': 'DEBUG',
                'level': 'ERROR',
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
            'botocore': {'level': 'ERROR'},
            # Suppress 'Using selector: EpollSelector'
            'asyncio': {
                'level': 'WARNING',
            },
        },
    }
)

logging.info(f'Starting EZID...')
logging.info(f'DEBUG MODE (settings.DEBUG) = {DEBUG}')

# Server instance

EZID_BASE_URL = 'http://localhost:8000'
DEFAULT_TARGET_BASE_URL = 'https://ezid.cdlib.org'
ALLOWED_HOSTS = ['*']
SECRET_KEY = '< placeholder - do not modify >'

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

NEWSFEED_URL = 'http://www.cdlib.org/cdlinfo/category/infrastructure-services/ezid/feed/'
NEWSFEED_POLLING_INTERVAL = 1800

# Sessions

SESSION_COOKIE_AGE = 7 * 24 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'
SESSION_COOKIE_PATH = '/'

# EZID administrator account

# Note: The `diag-update-admin` management command must be run in order to apply
# changes made to any of the `ADMIN_` settings. E.g.,
#
# $ cd ezid
# $ ./manage.py diag-update-admin

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'

ADMIN_GROUPNAME = 'admin'
ADMIN_NOTES = ''
ADMIN_EMAIL = 'ezid@ucop.edu'
ADMIN_DISPLAY_NAME = 'EZID superuser'

ADMIN_ORG_ACRONYM = 'CDL'
ADMIN_ORG_NAME = 'EZID'
ADMIN_ORG_URL = 'http://ezid.cdlib.org/'

ADMIN_CROSSREF_EMAIL = ''
ADMIN_CROSSREF_ENABLED = False

ADMIN_PRIMARY_CONTACT_EMAIL = 'ezid@ucop.edu'
ADMIN_PRIMARY_CONTACT_NAME = 'EZID superuser'
ADMIN_PRIMARY_CONTACT_PHONE = ''

ADMIN_SECONDARY_CONTACT_EMAIL = ''
ADMIN_SECONDARY_CONTACT_NAME = ''
ADMIN_SECONDARY_CONTACT_PHONE = ''

ADMIN_REALM = 'CDL'
ADMIN_USER_PID = 'ark:/99166/p9kw57h4w'
ADMIN_GROUP_PID = 'ark:/99166/p9g44hq02'

# Credentials
MATOMO_SITE_ID = None
MATOMO_SITE_URL = 'https://matomo.cdlib.org/'

S3_BUCKET = 'uc3-ezidui-dev'
S3_BUCKET_DOWNLOAD_PATH = 'download'

GZIP_COMMAND = '/usr/bin/gzip'
ZIP_COMMAND = '/usr/bin/zip'

# The ARK resolvers correspond to the above binders.
RESOLVER_DOI = 'https://doi.org'
RESOLVER_ARK = 'https://n2t-stg.n2t.net'

# Shoulders
SHOULDERS_ARK_TEST = 'ark:/99999/fk4'
SHOULDERS_DOI_TEST = 'doi:10.5072/FK2'
SHOULDERS_CROSSREF_TEST = 'doi:10.15697/'
SHOULDERS_AGENT = 'ark:/99166/p9'

TEST_SHOULDER_DICT = [
    {"namespace": 'ARK Test', "prefix": 'ark:/99999/fk4'},
    {"namespace": 'DOI Test', "prefix": 'doi:10.5072/FK2'},
]

PROTO_SUPER_SHOULDER = {
    "doi:10.7286/": "doi:10.7286/V1",
    "doi:10.4246/": "doi:10.4246/P6",
    "ark:/88435/": "ark:/88435/dc",
    "doi:10.15697/": "doi:10.15697/FK2",
    "ark:/12345/": "ark:/12345/fk8",
}

# DataCite

DATACITE_ENABLED = True
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
# daemon thread runs. The flag below governs if the daemon actually
# contacts Crossref, or if Crossref calls are simply short-circuited.
CROSSREF_ENABLED = True
CROSSREF_DEPOSITOR_NAME = 'EZID'
CROSSREF_DEPOSITOR_EMAIL = 'ezidcdl@gmail.com'
CROSSREF_REAL_SERVER = 'https://doi.crossref.org'
CROSSREF_TEST_SERVER = 'https://test.crossref.org'
CROSSREF_DEPOSIT_PATH = '/servlet/deposit'
CROSSREF_RESULTS_PATH = '/servlet/submissionDownload'
CROSSREF_USERNAME = ''
CROSSREF_PASSWORD = ''

# Profiles

DEFAULT_ARK_PROFILE = 'erc'
DEFAULT_DOI_PROFILE = 'datacite'
DEFAULT_UUID_PROFILE = 'erc'

PROFILES_KEYS = ['INTERNAL', 'DATACITE', 'DC', 'ERC', 'CROSSREF']

# The INTERNAL profile is special and must be listed first.
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
LINKCHECKER_RESULTS_UPLOAD_CYCLE = 64800
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
# link. Set to a negative value to make unlimited.
LINKCHECKER_MAX_READ = 104_857_600

# Internal settings

# Changes in these settings may require corresponding source code modifications.

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

INSTALLED_APPS = [
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

# Django 3.2 transitions from using a 32-bit counter for the automatically generated primary
# key, to using a 64-bit counter.
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

QUERY_PAGE_SIZE = 10000

# print('Installing exception hook')
# import impl.nog.tb
# sys.excepthook = impl.nog.tb.traceback_with_local_vars
