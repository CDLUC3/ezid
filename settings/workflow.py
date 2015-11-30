from common import *

DEPLOYMENT_LEVEL = "workflow"

DEBUG = False

ALLOWED_HOSTS = ["ias-ezid-wf-stg.cdlib.org"]

injectSecrets(DEPLOYMENT_LEVEL)
