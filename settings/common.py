import ldap
import os
import os.path
import socket
import sys

PROJECT_ROOT = os.path.split(os.path.split(os.path.abspath(__file__))[0])[0]
SITE_ROOT = os.path.split(PROJECT_ROOT)[0]
SETTINGS_DIR = os.path.join(PROJECT_ROOT, "settings")
EZID_CONFIG_FILE = os.path.join(SETTINGS_DIR, "ezid.conf")
EZID_SHADOW_CONFIG_FILE = EZID_CONFIG_FILE + ".shadow"
LOGGING_CONFIG_FILE = "logging.server.conf"

sys.path.append(os.path.join(PROJECT_ROOT, "code"))

# Workaround for an obscure Django bug: when running under Apache (and
# only under Apache), certain rewriting of the request URL (for
# example, replacement of double slashes with single slashes) messes
# up Django's URL processing, causing HttpRequest.path to not match
# the urlpattern corresponding to the invoked callback function.  See
# django.core.handlers.base.get_script_name.
FORCE_SCRIPT_NAME = "/ezid"

ldap.set_option(ldap.OPT_X_TLS_CACERTDIR, os.path.join(PROJECT_ROOT,
  "settings", "certs"))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
  ("Greg Janee", "gjanee@ucop.edu"),
  ("John Kunze", "john.kunze@ucop.edu"),
  ("Scott Fisher", "sfisher@ucop.edu")
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
    "NAME": os.path.join(SITE_ROOT, "db", "django.sqlite3")
  }
}

TIME_ZONE = "America/Los_Angeles"

MEDIA_ROOT = os.path.join(PROJECT_ROOT, "static")
MEDIA_URL = "static/"

INFO_STATIC = os.path.join(PROJECT_ROOT, "templates/info/static")

SECRET_KEY = "ah2l_w1)ejdxor=0198d$1k$9gdqccsza@4@lqiii2%@!2)m1u"

STANDALONE = False
SSL = True

MIDDLEWARE_CLASSES = (
  "django.middleware.common.CommonMiddleware",
  "django.contrib.sessions.middleware.SessionMiddleware",
  "django.contrib.messages.middleware.MessageMiddleware",
  "middleware.SslMiddleware"
)

ROOT_URLCONF = "settings.urls"

RSS_FEED =\
  "http://www.cdlib.org/cdlinfo/category/digital-preservation/feed/?s=ezid"

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

TEMPLATE_LOADERS =\
  ("django.template.loaders.filesystem.Loader",
   "django.template.loaders.app_directories.load_template_source")
TEMPLATE_DIRS = (os.path.join(PROJECT_ROOT, "templates"),)
TEMPLATE_CONTEXT_PROCESSORS =\
  ("django.contrib.messages.context_processors.messages",
   "django.core.context_processors.request")

INSTALLED_APPS = (
  "django.contrib.sessions",
  "django.contrib.messages",
  "ui_tags"
)

SESSION_COOKIE_PATH = "/ezid/"

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"
