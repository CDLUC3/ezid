from common import *

DEPLOYMENT_LEVEL = "staging"

DEBUG = False

ALLOWED_HOSTS = ["ias-ezid-stg.cdlib.org"]

injectSecrets(DEPLOYMENT_LEVEL)
