from .common import *

DEPLOYMENT_LEVEL = "production"

DEBUG = False

ADMINS.append(("Marisa Strong", "marisa.strong@ucop.edu"))
ADMINS.append(("Maria Gould", "maria.gould@ucop.edu"))

ALLOWED_HOSTS = ['*']

#ALLOWED_HOSTS = [
#        "localhost",
#        "127.0.0.1",
#        "172.30.43.85",
#        "ezid.cdlib.org",
#        "uc3-ezid-ui-prd.cdlib.org",
#        "uc3-ezidui01x2-prd.cdlib.org",
#        "uc3-ezidui01x2-prd.cdlib.org:18880",
#        'uc3-ezidui01x2-prd:18880',
#        'uc3-ezidui01x2-prd',
#        ]

injectSecrets(DEPLOYMENT_LEVEL)
