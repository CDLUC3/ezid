import os.path
import sys

PROJECT_ROOT = os.path.split(os.path.split(os.path.abspath(__file__))[0])[0]
SITE_ROOT = os.path.split(PROJECT_ROOT)[0]
EZID_CONFIG_FILE = os.path.join(PROJECT_ROOT, "settings", "ezid.conf")

sys.path.append(os.path.join(PROJECT_ROOT, "code"))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
  ("Greg Janee", "gjanee@ucop.edu"),
  ("John Kunze", "john.kunze@ucop.edu")
)
MANAGERS = ADMINS
SERVER_EMAIL = "ezid@n2t.net"
SEND_BROKEN_LINK_EMAILS = True

DATABASE_ENGINE = "sqlite3"
DATABASE_NAME = os.path.join(SITE_ROOT, "db", "db.sqlite3")

TIME_ZONE = "America/Los_Angeles"

MEDIA_ROOT = os.path.join(PROJECT_ROOT, "static")
MEDIA_URL = "static/"

SECRET_KEY = "ah2l_w1)ejdxor=0198d$1k$9gdqccsza@4@lqiii2%@!2)m1u"

SSL = True

MIDDLEWARE_CLASSES = (
  "django.middleware.common.CommonMiddleware",
  "django.contrib.sessions.middleware.SessionMiddleware",
  "django.contrib.messages.middleware.MessageMiddleware",
  "middleware.SslMiddleware"
)

ROOT_URLCONF = "settings.urls"

TEMPLATE_LOADERS = ("django.template.loaders.filesystem.load_template_source",)
TEMPLATE_DIRS = (os.path.join(PROJECT_ROOT, "templates"),)
TEMPLATE_CONTEXT_PROCESSORS =\
  ("django.contrib.messages.context_processors.messages",)

INSTALLED_APPS = (
  "django.contrib.sessions",
  "django.contrib.messages"
)

SESSION_COOKIE_PATH = "/ezid/"

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"
