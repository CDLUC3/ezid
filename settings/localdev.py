from common import *

DEPLOYMENT_LEVEL = "localdev"

STANDALONE = True
SSL = False
RELOAD_TEMPLATES = True

ALLOWED_HOSTS = ["localhost"]
LOCALIZATIONS = { "default": ("cdl", ["andy.mardesich@ucop.edu"]) }
LOCALIZATIONS["localhost:8001"] = ("purdue", ["gjanee@ucop.edu"])
LOCALIZATIONS["localhost:8002"] = ("jisc-edina", ["gjanee@ucop.edu"])

injectSecrets(DEPLOYMENT_LEVEL)

# Andy's mysql driver won't allow utf8mb4. Force utf8
DATABASES["search"]["OPTIONS"]["charset"] = "utf8"
