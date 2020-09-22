"""Settings for unit tests

These settings are active while tests are running under pytest.

This file contains all the settings required by EZID and Django specified directly.
EZID's custom configuration system is not used.

pytest finds this file via the DJANGO_SETTINGS_MODULE setting in ~/tox.ini.
"""
import logging
import logging.config
import os.path
import socket
import sys

import django.utils.translation

STANDALONE = True
DAEMON_THREADS_ENABLED = False
LOCALIZATIONS = {"default": ("cdl", ["ezid@ucop.edu"])}
PROJECT_ROOT = os.path.split(os.path.split(os.path.abspath(__file__))[0])[0]
SITE_ROOT = os.path.split(PROJECT_ROOT)[0]
DOWNLOAD_WORK_DIR = os.path.join(SITE_ROOT, "download")
DOWNLOAD_PUBLIC_DIR = os.path.join(DOWNLOAD_WORK_DIR, "public")
SETTINGS_DIR = os.path.join(PROJECT_ROOT, "settings")
EZID_CONFIG_FILE = os.path.join(SETTINGS_DIR, "test_config.conf")
EZID_SHADOW_CONFIG_FILE = '/dev/null'
DEPLOYMENT_LEVEL = 'local'
MINTERS_PATH = os.path.join(PROJECT_ROOT, "db", "minters")

sys.path.append(os.path.join(PROJECT_ROOT, "impl"))

DEBUG = True
TEST_RUNNER = None

MANAGERS = ADMINS = []

ADMIN_USER = 'admin'
ADMIN_PW = 'admin'

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    'testserver',  # Travis
    "uc3-ezidx2-dev.cdlib.org",
]

if "HOSTNAME" in os.environ:
    SERVER_EMAIL = "ezid@" + os.environ["HOSTNAME"]
else:
    SERVER_EMAIL = "ezid@" + socket.gethostname()

ALLOWED_HOSTS = []

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "HOST": "localhost",
        "NAME": "ezid_tests",
        "USER": "ezid_test_user",
        "PASSWORD": "",
        # "AUTOCOMMIT": False,
        "ATOMIC_REQUESTS": False,
        "OPTIONS": {"charset": "utf8mb4"},
        'DATABASE_OPTIONS': {'unix_socket': '/tmp/mysql.sock',},
    },
    "search": {
        "ENGINE": "django.db.backends.mysql",
        "HOST": "localhost",
        "NAME": "ezid_tests",
        "USER": "ezid_test_user",
        "PASSWORD": "",
        # "AUTOCOMMIT": False,
        "ATOMIC_REQUESTS": False,
        "OPTIONS": {"charset": "utf8mb4"},
        'DATABASE_OPTIONS': {'unix_socket': '/tmp/mysql.sock',},
        "fulltextSearchSupported": True,
    },
}

SEARCH_STORE_SAME_DATABASE = True

DATABASE_ROUTERS = ["settings.routers.Router"]

TIME_ZONE = "America/Los_Angeles"
TIME_FORMAT_UI_METADATA = "%Y-%m-%d %H:%M:%S"

STATIC_ROOT = os.path.join(PROJECT_ROOT, "static")
STATIC_URL = "/static/"

LANGUAGES = [
    ("en", django.utils.translation.ugettext_lazy("English")),
    ("fr-CA", django.utils.translation.ugettext_lazy("Canadian French")),
]
LOCALE_PATHS = [os.path.join(STATIC_ROOT, "locale")]

LANGUAGE_CODE = 'en'

SECRET_KEY = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "userauth.LdapSha1PasswordHasher",
]

MIDDLEWARE_CLASSES = (
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "middleware.ExceptionScrubberMiddleware",
)

ROOT_URLCONF = "settings.urls"

SESSION_COOKIE_PATH = "/"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 7 * 86400
SESSION_SERIALIZER = "django.contrib.sessions.serializers.PickleSerializer"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(PROJECT_ROOT, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
            ]
        },
    }
]

INSTALLED_APPS = [
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "ui_tags",
    "ezidapp",
]

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"


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
                'format': '%(levelname)8s %(module)s %(process)d %(thread)s %(message)s',
            },
            'simple': {'format': '%(levelname)8s %(message)s'},
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
                'stream': sys.stdout,
            },
        },
        'loggers': {
            '': {'handlers': ['console'], 'propagate': True, 'level': 'DEBUG',},
            # Increase logging level on loggers that are noisy at debug level
            'django.request': {
                'handlers': ['console'],
                'propagate': False,
                'level': 'ERROR',
            },
            'filelock': {
                'handlers': ['console'],
                'propagate': False,
                'level': 'ERROR',
            },
        },
    }
)

# Ensure that user 'admin' with password 'admin' exists and is an admin
# import ezidapp.models
# store_user_model = ezidapp.models.StoreUser.objects.update_or_create(
#     name='admin',
#     password='admin',
#     displayName='Test Admin',
#     isSuperuser=True,
#     loginEnabled=True,
# )
#

# These messages should always make it to stdout
sys.__stdout__.write('{}\n'.format('-' * 100))
sys.__stdout__.write('The next 3 lines should contain DEBUG, INFO AND ERROR level\n')
sys.__stdout__.write('test messages from logging:\n')
log = logging.getLogger(__name__)
log.debug('DEBUG level test message')
log.info('INFO level test message')
log.error('ERROR level test message')
