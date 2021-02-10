from common import *

DEPLOYMENT_LEVEL = "staging"

DEBUG = False

ALLOWED_HOSTS = ['*']

injectSecrets(DEPLOYMENT_LEVEL)
