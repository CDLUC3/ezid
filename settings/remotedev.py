import ldap
import os.path

from common import *

DEPLOYMENT_LEVEL = "remotedev"

STANDALONE = True
USE_SSL = False

ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

STORE_MYSQL = False
if STORE_MYSQL:
  DATABASES["default"]["HOST"] = "127.0.0.1"
  SECRET_PATHS.remove(("DATABASES", "default", "HOST"))
else:
  DATABASES["default"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": os.path.join(SITE_ROOT, "db", "store.sqlite3"),
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
    "NAME": os.path.join(SITE_ROOT, "db", "search.sqlite3"),
    "OPTIONS": { "timeout": 60 },
    "fulltextSearchSupported": False
  }
  SECRET_PATHS.remove(("DATABASES", "search", "HOST"))
  SECRET_PATHS.remove(("DATABASES", "search", "PASSWORD"))

ALLOWED_HOSTS = ["localhost"]
LOCALIZATIONS["localhost:8001"] = ("purdue", ["gjanee@ucop.edu"])
LOCALIZATIONS["localhost:8002"] = ("jisc-edina", ["gjanee@ucop.edu"])

injectSecrets(DEPLOYMENT_LEVEL)
