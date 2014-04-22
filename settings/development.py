from common import *

DEPLOYMENT_LEVEL = "development"

ALLOWED_HOSTS = ["ezid-dev.cdlib.org", "ezid-dev-alt.cdlib.org"]

# Select one localization below to be triggered by the alt hostname:
# LOCALIZATIONS["ezid-dev-alt.cdlib.org"] = ("purdue", ["gjanee@ucop.edu"])
LOCALIZATIONS["ezid-dev-alt.cdlib.org"] = ("jisc-edina", ["gjanee@ucop.edu"])
