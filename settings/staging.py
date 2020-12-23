from .common import *

DEPLOYMENT_LEVEL = "staging"

DEBUG = False

ALLOWED_HOSTS = ["uc3-ezidx2-stg.cdlib.org"]

injectSecrets(DEPLOYMENT_LEVEL)
