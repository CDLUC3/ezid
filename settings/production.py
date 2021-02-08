import settings.common

DEPLOYMENT_LEVEL = "production"

DEBUG = False

settings.common.ADMINS.append(("Marisa Strong", "marisa.strong@ucop.edu"))
settings.common.ADMINS.append(("Maria Gould", "maria.gould@ucop.edu"))

ALLOWED_HOSTS = ['*']

# ALLOWED_HOSTS = [
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

settings.common.injectSecrets(DEPLOYMENT_LEVEL)
