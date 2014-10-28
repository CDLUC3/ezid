import ldap
import os
import os.path
import random
import socket
import sys

# EZID-specific paths...
PROJECT_ROOT = os.path.split(os.path.split(os.path.abspath(__file__))[0])[0]
SITE_ROOT = os.path.split(PROJECT_ROOT)[0]
SETTINGS_DIR = os.path.join(PROJECT_ROOT, "settings")
EZID_CONFIG_FILE = os.path.join(SETTINGS_DIR, "ezid.conf")
EZID_SHADOW_CONFIG_FILE = EZID_CONFIG_FILE + ".shadow"
LOGGING_CONFIG_FILE = "logging.server.conf"

sys.path.append(os.path.join(PROJECT_ROOT, "code"))

ldap.set_option(ldap.OPT_X_TLS_CACERTDIR, os.path.join(PROJECT_ROOT,
  "settings", "certs"))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
  ("Greg Janee", "gjanee@ucop.edu"),
  ("John Kunze", "john.kunze@ucop.edu")
)
MANAGERS = ADMINS

if "HOSTNAME" in os.environ:
  SERVER_EMAIL = "ezid@" + os.environ["HOSTNAME"]
else:
  SERVER_EMAIL = "ezid@" + socket.gethostname()

SEND_BROKEN_LINK_EMAILS = True

DATABASES = {
  "default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": os.path.join(SITE_ROOT, "db", "django.sqlite3"),
    "OPTIONS": { "timeout": 60 }
  }
}

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
  "middleware.SslMiddleware"
)

ROOT_URLCONF = "settings.urls"

SESSION_COOKIE_PATH = "/"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 7*86400
SESSION_SERIALIZER = "django.contrib.sessions.serializers.PickleSerializer"

TEMPLATE_LOADERS =\
  ("django.template.loaders.filesystem.Loader",
   "django.template.loaders.app_directories.Loader")
TEMPLATE_DIRS = (os.path.join(PROJECT_ROOT, "templates"),)
TEMPLATE_CONTEXT_PROCESSORS =\
  ("django.contrib.messages.context_processors.messages",
   "django.core.context_processors.request")

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
