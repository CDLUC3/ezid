import ldap
import os.path

from common import *

DEPLOYMENT_LEVEL = "remotedev"

STANDALONE = True
SSL = False

ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

MYSQL = False

if MYSQL:
  DATABASES["search"]["HOST"] = "127.0.0.1"
  del SECRET_PATHS[0]
else:
  DATABASES["search"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": os.path.join(SITE_ROOT, "db", "search.sqlite3"),
    "OPTIONS": { "timeout": 60 }
  }
  del SECRET_PATHS[0:len(SECRET_PATHS)]

ALLOWED_HOSTS = ["localhost"]
LOCALIZATIONS["localhost:8001"] = ("purdue", ["gjanee@ucop.edu"])
LOCALIZATIONS["localhost:8002"] = ("jisc-edina", ["gjanee@ucop.edu"])

injectSecrets(DEPLOYMENT_LEVEL)
