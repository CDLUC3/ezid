from common import *

DEPLOYMENT_LEVEL = "production"

DEBUG = False

ADMINS.append(("Marisa Strong", "marisa.strong@ucop.edu"))
ADMINS.append(("Perry Willett", "perry.willett@ucop.edu"))

ALLOWED_HOSTS = ["ezid.cdlib.org", "ezid.lib.purdue.edu"]
LOCALIZATIONS["ezid.lib.purdue.edu"] = ("purdue", ["datacite@purdue.edu"])

injectSecrets(DEPLOYMENT_LEVEL)
