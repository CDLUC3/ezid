import ldap

from common import *

DEPLOYMENT_LEVEL = "uidev_scott"

FORCE_SCRIPT_NAME = None

STANDALONE = True

SSL = False

#setting RELOAD_TEMPLATES to True makes templates reload on each
#page load so you don't have to restart the server to see
#template changes. A time-saver for iterative changes in development.
RELOAD_TEMPLATES = True

#This tells a special template tag to substitute
#one templates for another with the same filename in a different
#customization directory.  Customization is based on host name.

HOST_TEMPLATE_CUSTOMIZATION = {'localhost:8001': 'purdue'}

ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
