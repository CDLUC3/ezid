from common import *

DEPLOYMENT_LEVEL = "development"

ALLOWED_HOSTS = ["ias-ezid-dev.cdlib.org", "ezid-dev-alt-aws.cdlib.org"]

# Select one localization below to be triggered by the alt hostname:
# ToDo: Change this back to gjanee@ucop.edu after demo
LOCALIZATIONS["ezid-dev-alt-aws.cdlib.org"] = ("purdue", ["datacite@purdue.edu"])
# LOCALIZATIONS["ezid-dev-alt-aws.cdlib.org"] =\
#  ("jisc-edina", ["gjanee@ucop.edu"])

injectSecrets(DEPLOYMENT_LEVEL)
