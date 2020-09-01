"""Settings for unit tests

These settings are active while tests are running under pytest.

This file contains all the settings required by EZID and Django specified directly.
EZID's custom configuration system is not used.

pytest finds this file via the DJANGO_SETTINGS_MODULE setting in ~/tox.ini.
"""

import os.path
import socket
import sys

import django.utils.translation

STANDALONE = False
DAEMON_THREADS_ENABLED = False
LOCALIZATIONS = {"default": ("cdl", ["ezid@ucop.edu"])}

PROJECT_ROOT = os.path.split(os.path.split(os.path.abspath(__file__))[0])[0]
SITE_ROOT = os.path.split(PROJECT_ROOT)[0]
DOWNLOAD_WORK_DIR = os.path.join(SITE_ROOT, "download")
DOWNLOAD_PUBLIC_DIR = os.path.join(DOWNLOAD_WORK_DIR, "public")
SETTINGS_DIR = os.path.join(PROJECT_ROOT, "settings")
EZID_CONFIG_FILE = os.path.join(SETTINGS_DIR, "test_config.conf")
EZID_SHADOW_CONFIG_FILE = '/dev/null' #EZID_CONFIG_FILE + ".shadow"
DEPLOYMENT_LEVEL='local'
LOGGING_CONFIG_FILE = "test_logging.conf"
MINTERS_PATH = os.path.join(PROJECT_ROOT, "db", "minters")

sys.path.append(os.path.join(PROJECT_ROOT, "impl"))

DEBUG = True
TEST_RUNNER = None

MANAGERS = ADMINS = []

ADMIN_USER = 'admin'
ADMIN_PW = 'admin'

ALLOWED_HOSTS = [
        'testserver',
        ]


if "HOSTNAME" in os.environ:
    SERVER_EMAIL = "ezid@" + os.environ["HOSTNAME"]
else:
    SERVER_EMAIL = "ezid@" + socket.gethostname()

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
        'DATABASE_OPTIONS': {'unix_socket': '/tmp/mysql.sock', },
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
        'DATABASE_OPTIONS': {'unix_socket': '/tmp/mysql.sock', },
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

LOGGING = {
    'version': 1,
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
        },
    },
    'loggers': {
        '': {'handlers': ['console'], 'propagate': True, 'level': 'INFO',},
        # Silence loggers that are noisy at debug level
        'django.request': {
            'handlers': ['console'],
            'propagate': False,
            'level': 'ERROR',  # WARN also shows 404 errors
        },
        'filelock': {
            'handlers': ['console'],
            'propagate': False,
            'level': 'ERROR',  # WARN also shows 404 errors
        },
    },
}
