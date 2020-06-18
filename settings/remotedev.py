import os.path

from common import *

DEPLOYMENT_LEVEL = "remotedev"

STANDALONE = True

STORE_MYSQL = False
if STORE_MYSQL:
  DATABASES["default"]["HOST"] = "127.0.0.1"
  SECRET_PATHS.remove(("DATABASES", "default", "HOST"))
else:
  DATABASES["default"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "HOST": "databases.store_host",
    "NAME": os.path.join(PROJECT_ROOT, "..", "db", "store.sqlite3"),
    "OPTIONS": { "timeout": 60 }
  }
  SECRET_PATHS.remove(("DATABASES", "default", "HOST"))
  SECRET_PATHS.remove(("DATABASES", "default", "PASSWORD"))

SEARCH_MYSQL = False
if SEARCH_MYSQL:
  DATABASES["search"]["HOST"] = "127.0.0.1"
  SECRET_PATHS.remove(("DATABASES", "search", "HOST"))
else:
  DATABASES["search"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "HOST": "databases.store_host",
    "NAME": os.path.join(PROJECT_ROOT, "..", "db", "search.sqlite3"),
    "OPTIONS": { "timeout": 60 },
    "fulltextSearchSupported": False
  }
  SECRET_PATHS.remove(("DATABASES", "search", "HOST"))
  SECRET_PATHS.remove(("DATABASES", "search", "PASSWORD"))

SEARCH_STORE_SAME_DATABASE = STORE_MYSQL and SEARCH_MYSQL

ALLOWED_HOSTS = ["uc3-ezidx2-dev.cdlib.org","localhost"]

injectSecrets(DEPLOYMENT_LEVEL)
