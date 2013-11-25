import ldap

from common import *

DEPLOYMENT_LEVEL = "uidev_scott"

FORCE_SCRIPT_NAME = None

STANDALONE = True
SSL = False

# Reload templates on each page load.
RELOAD_TEMPLATES = True

ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

ALLOWED_HOSTS = ["localhost"]
LOCALIZATIONS["localhost:8001"] = ("purdue", ["scott.fisher@ucop.edu"])
