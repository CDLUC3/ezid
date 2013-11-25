import ldap

from common import *

DEPLOYMENT_LEVEL = "localdev"

FORCE_SCRIPT_NAME = None

STANDALONE = True
SSL = False

ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

ALLOWED_HOSTS = ["localhost"]
LOCALIZATIONS["localhost:8001"] = ("purdue", ["gjanee@ucop.edu"])
