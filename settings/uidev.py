import ldap

from common import *

DEPLOYMENT_LEVEL = "uidev"

# FORCE_SCRIPT_NAME = None
 
# STANDALONE = True

SSL = True 

ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
