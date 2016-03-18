import ldap
import os
import os.path
import random
import socket
import sys

# EZID-specific paths...
PROJECT_ROOT = os.path.split(os.path.split(os.path.abspath(__file__))[0])[0]
SITE_ROOT = os.path.split(PROJECT_ROOT)[0]
DOWNLOAD_WORK_DIR = os.path.join(SITE_ROOT, "download")
DOWNLOAD_PUBLIC_DIR = os.path.join(DOWNLOAD_WORK_DIR, "public")
SETTINGS_DIR = os.path.join(PROJECT_ROOT, "settings")
EZID_CONFIG_FILE = os.path.join(SETTINGS_DIR, "ezid.conf")
EZID_SHADOW_CONFIG_FILE = EZID_CONFIG_FILE + ".shadow"
LOGGING_CONFIG_FILE = "logging.server.conf"

sys.path.append(os.path.join(PROJECT_ROOT, "code"))

ldap.set_option(ldap.OPT_X_TLS_CACERTDIR, os.path.join(PROJECT_ROOT,
  "settings", "certs"))
ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_DEMAND)

DEBUG = True
TEST_RUNNER = "django.test.runner.DiscoverRunner"

MANAGERS = ADMINS = (
  ("Greg Janee", "gjanee@ucop.edu"),
  ("John Kunze", "john.kunze@ucop.edu")
)

if "HOSTNAME" in os.environ:
  SERVER_EMAIL = "ezid@" + os.environ["HOSTNAME"]
else:
  SERVER_EMAIL = "ezid@" + socket.gethostname()

DATABASES = {
  # To keep the Django admin app happy, the store database must be
  # referred to as 'default', despite our use of a router below.
  "default": {
    "ENGINE": "django.db.backends.mysql",
    "HOST": "databases.store_host", # see below
    "NAME": "ezid",
    "USER": "ezidrw",
    "PASSWORD": "databases.store_password", # see below
    "OPTIONS": { "charset": "utf8mb4" }
  },
  "search": {
    "ENGINE": "django.db.backends.mysql",
    "HOST": "databases.search_host", # see below
    "NAME": "ezid",
    "USER": "ezidrw",
    "PASSWORD": "databases.search_password", # see below
    "OPTIONS": { "charset": "utf8mb4" },
    "fulltextSearchSupported": True
  }
}
DATABASE_ROUTERS = ["settings.routers.Router"]

TIME_ZONE = "America/Los_Angeles"
TIME_FORMAT_UI_METADATA = "%Y-%m-%d %H:%M:%S"

MEDIA_ROOT = os.path.join(PROJECT_ROOT, "static")
MEDIA_URL = "static/"

def _loadSecretKey ():
  try:
    f = open(os.path.join(SITE_ROOT, "db", "secret_key"))
    k = f.read().strip()
    f.close()
  except IOError:
    rng = random.SystemRandom()
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
    k = "".join(rng.choice(alphabet) for i in range(50))
    try:
      f = open(os.path.join(SITE_ROOT, "db", "secret_key"), "w")
      f.write(k + "\n")
      f.close()
    except IOError:
      pass
  return k

SECRET_KEY = _loadSecretKey()

MIDDLEWARE_CLASSES = (
  "django.middleware.common.CommonMiddleware",
  "django.contrib.sessions.middleware.SessionMiddleware",
  "django.contrib.messages.middleware.MessageMiddleware",
  "middleware.SslMiddleware",
  "middleware.ExceptionScrubberMiddleware"
)

ROOT_URLCONF = "settings.urls"

SESSION_COOKIE_PATH = "/"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 7*86400
SESSION_SERIALIZER = "django.contrib.sessions.serializers.PickleSerializer"

TEMPLATES = [
  { "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [os.path.join(PROJECT_ROOT, "templates")],
    "APP_DIRS": True,
    "OPTIONS": {
      "context_processors": [
        "django.contrib.messages.context_processors.messages",
        "django.template.context_processors.request"]
    }
  }
]

INSTALLED_APPS = (
  "django.contrib.sessions",
  "django.contrib.messages",
  "ezidapp",
  "ui_tags"
)

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# EZID-specific settings...
STANDALONE = False
SSL = True
DAEMON_THREADS_ENABLED = True
LOCALIZATIONS = { "default": ("cdl", ["ezid@ucop.edu"]) }

# The following is a necessarily cockamamie scheme to get passwords
# and other sensitive information from the EZID configuration system
# into this file.  'injectSecrets' should be called by the settings
# module corresponding to the deployment level, after all settings are
# in place.

SECRET_PATHS = [
  ("DATABASES", "default", "HOST"),
  ("DATABASES", "default", "PASSWORD"),
  ("DATABASES", "search", "HOST"),
  ("DATABASES", "search", "PASSWORD")
]

def injectSecrets (deploymentLevel):
  import config_loader
  config = config_loader.Config(SITE_ROOT, PROJECT_ROOT,
    EZID_CONFIG_FILE, EZID_SHADOW_CONFIG_FILE, deploymentLevel)
  for path in SECRET_PATHS:
    o = sys.modules["settings.common"] # this module
    for p in path[:-1]:
      if type(p) is str and hasattr(o, p):
        o = getattr(o, p)
      else:
        o = o[p]
    if type(path[-1]) is str and hasattr(o, path[-1]):
      setattr(o, path[-1], config.getOption(getattr(o, path[-1])))
    else:
      o[path[-1]] = config.getOption(o[path[-1]])
