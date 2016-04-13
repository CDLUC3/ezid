from common import *

DEPLOYMENT_LEVEL = "production"

DEBUG = False

ADMINS.append(("John Kunze", "john.kunze@ucop.edu"))

ALLOWED_HOSTS = ["ezid.cdlib.org", "ezid.lib.purdue.edu",
  "ezid-edina.cdlib.org"]
LOCALIZATIONS["ezid.lib.purdue.edu"] = ("purdue", ["datacite@purdue.edu"])
LOCALIZATIONS["ezid-edina.cdlib.org"] = ("jisc-edina", ["edina@ed.ac.uk"])

injectSecrets(DEPLOYMENT_LEVEL)
