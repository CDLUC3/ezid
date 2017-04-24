from common import *

DEPLOYMENT_LEVEL = "development"

ALLOWED_HOSTS = ["ids-ezid-dev.cdlib.org", "ezid-dev-alt-aws.cdlib.org"]

# Select one localization below to be triggered by the alt hostname:
# LOCALIZATIONS["ezid-dev-alt-aws.cdlib.org"] = ("purdue", ["gjanee@ucop.edu"])
LOCALIZATIONS["ezid-dev-alt-aws.cdlib.org"] =\
  ("jisc-edina", ["gjanee@ucop.edu"])

injectSecrets(DEPLOYMENT_LEVEL)
